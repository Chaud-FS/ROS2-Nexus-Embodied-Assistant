"""LLM decision brain node.

Consumes:
  * /nexus/voice/text          (natural-language instruction)
  * /nexus/perception/result  (scene from Qwen-VL)
  * /nexus/arm/state          (current joint state)
  * /nexus/execution/result   (outcome reported by the orchestrator)

Produces:
  * /nexus/brain/plan         (structured TaskPlan for the orchestrator)
  * /nexus/brain/feedback     (spoken-language summary for the TTS module)
"""
from __future__ import annotations

import json
import os
from typing import Optional

import rclpy
from nexus_interfaces.msg import PerceptionResult, PlanStep, TaskPlan
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .llm_client import LLMClient


class LLMBrainNode(Node):
    def __init__(self) -> None:
        super().__init__("llm_brain_node")

        self.declare_parameter("api_key", "")
        self.declare_parameter("model", "qwen-plus")
        self.declare_parameter("base_url", "")
        self.declare_parameter("voice_topic", "/nexus/voice/text")
        self.declare_parameter("perception_topic", "/nexus/perception/result")
        self.declare_parameter("arm_state_topic", "/nexus/arm/state")
        self.declare_parameter("plan_topic", "/nexus/brain/plan")
        self.declare_parameter("feedback_topic", "/nexus/brain/feedback")
        self.declare_parameter("exec_result_topic", "/nexus/execution/result")
        self.declare_parameter("plan_service", "/nexus/brain/plan")

        api_key = self.get_parameter("api_key").value or os.environ.get(
            "DASHSCOPE_API_KEY"
        ) or os.environ.get("OPENAI_API_KEY", "")
        model = self.get_parameter("model").value
        base_url = self.get_parameter("base_url").value or None

        self.client = LLMClient(api_key, model, base_url)
        self._task_counter = 0

        self.latest_scene: Optional[PerceptionResult] = None
        self.latest_joints: Optional[JointState] = None

        self.create_subscription(
            String, self.get_parameter("voice_topic").value, self._on_voice, 10
        )
        self.create_subscription(
            PerceptionResult, self.get_parameter("perception_topic").value,
            self._on_perception, 10
        )
        self.create_subscription(
            JointState, self.get_parameter("arm_state_topic").value,
            self._on_joints, 10
        )
        self.create_subscription(
            String, self.get_parameter("exec_result_topic").value,
            self._on_exec_result, 10
        )

        self.plan_pub = self.create_publisher(TaskPlan, self.get_parameter("plan_topic").value, 10)
        self.feedback_pub = self.create_publisher(
            String, self.get_parameter("feedback_topic").value, 10
        )
        self.create_service(
            Trigger, self.get_parameter("plan_service").value, self._on_plan_srv
        )

        self.get_logger().info(
            f"LLM brain ready (model={model}, key_set={bool(api_key)})."
        )

    # ---------------- subscriptions ---------------- #
    def _on_voice(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            return
        self.get_logger().info(f"Instruction received: {text}")
        plan = self._build_plan(text)
        if plan is not None:
            self.plan_pub.publish(plan)
            self.feedback_pub.publish(String(data=f"Planning: {plan.rationale}"))

    def _on_perception(self, msg: PerceptionResult) -> None:
        self.latest_scene = msg

    def _on_joints(self, msg: JointState) -> None:
        self.latest_joints = msg

    def _on_exec_result(self, msg: String) -> None:
        self.feedback_pub.publish(String(data=msg.data))

    def _on_plan_srv(self, _req: Trigger.Request, resp: Trigger.Response):
        plan = self._build_plan("Re-plan the last instruction.")
        if plan is not None:
            self.plan_pub.publish(plan)
            resp.success = True
            resp.message = plan.rationale
        else:
            resp.success = False
            resp.message = "planning failed"
        return resp

    # ---------------- planning ---------------- #
    def _scene_summary(self) -> str:
        if self.latest_scene is None:
            return "No perception data yet."
        lines = [f"description: {self.latest_scene.scene_description}"]
        for o in self.latest_scene.objects:
            p = o.pose.pose.position
            lines.append(
                f"- {o.name} (conf={o.confidence:.2f}) "
                f"pos=({p.x:.2f},{p.y:.2f},{p.z:.2f}) in {o.pose.header.frame_id}"
            )
        return "\n".join(lines)

    def _joint_summary(self) -> str:
        if self.latest_joints is None:
            return "joints: unknown"
        return ", ".join(
            f"{n}={v:.2f}" for n, v in zip(self.latest_joints.name, self.latest_joints.position)
        )

    def _build_plan(self, instruction: str) -> Optional[TaskPlan]:
        if self.latest_scene is None:
            self.get_logger().warn("No scene yet; triggering perception first.")
        user_prompt = (
            f"Instruction: {instruction}\n\n"
            f"Scene:\n{self._scene_summary()}\n\n"
            f"Current joints: {self._joint_summary()}\n\n"
            "Produce an executable plan."
        )
        raw = self.client.chat(user_prompt)
        try:
            data = self._extract_json(raw)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Failed to parse LLM output: {exc}\n{raw}")
            return None

        plan = TaskPlan()
        plan.header.stamp = self.get_clock().now().to_msg()
        plan.task_id = f"t_{self._task_counter:04d}"
        self._task_counter += 1
        plan.intent = data.get("intent", "unknown")
        plan.rationale = data.get("rationale", "")
        for s in data.get("steps", []):
            step = PlanStep()
            step.action = str(s.get("action", "wait"))
            step.target = str(s.get("target", ""))
            step.frame = str(s.get("frame", "base_link"))
            step.timeout = float(s.get("timeout", 5.0))
            plan.steps.append(step)
        self.get_logger().info(f"Plan {plan.task_id}: {plan.intent} ({len(plan.steps)} steps)")
        return plan

    @staticmethod
    def _extract_json(text: str) -> dict:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("no JSON in LLM output")
        return json.loads(text[start : end + 1])


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = LLMBrainNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
