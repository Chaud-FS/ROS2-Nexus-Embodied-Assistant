"""Multimodal orchestrator.

Bridges the LLM brain and the simulated robot:
  * Receives a TaskPlan on /nexus/brain/plan.
  * Translates each step into a concrete motion:
      - move_to <object/home/ready>: resolve a pose (via TF + IK) or a
        named joint configuration, then drive arm_controller.
      - grasp / release: drive gripper_controller.
      - home: return to the home joint pose.
      - wait: brief pause.
  * Reports execution outcomes on /nexus/execution/result for the brain/TTS.

All motion calls are asynchronous (action/service futures + callbacks) so the
node never blocks the executor and can process streaming commands.
"""
from __future__ import annotations

import math
from typing import List, Optional

import rclpy
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import PoseStamped, Quaternion
from moveit_msgs.msg import MoveItErrorCodes
from moveit_msgs.srv import GetPositionIK
from nexus_interfaces.msg import PerceptionResult, TaskPlan
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener
from tf2_ros import TransformException
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

ARM_JOINTS = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
GRIPPER_JOINTS = ["left_finger_joint", "right_finger_joint"]
ARM_ACTION = "/nexus/arm_controller/follow_joint_trajectory"
GRIPPER_ACTION = "/nexus/gripper_controller/follow_joint_trajectory"
IK_SERVICE = "/compute_ik"

HOME_JOINTS = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
READY_JOINTS = [0.0, -0.3, 0.6, -0.3, 0.0, 0.0]
GRIPPER_OPEN = [0.04, -0.04]   # left +0.04, right mirrored by mimic
GRIPPER_CLOSED = [0.005, -0.005]


class OrchestratorNode(Node):
    def __init__(self) -> None:
        super().__init__("nexus_orchestrator")

        self.declare_parameter("plan_topic", "/nexus/brain/plan")
        self.declare_parameter("perception_topic", "/nexus/perception/result")
        self.declare_parameter("joint_state_topic", "/nexus/joint_states")
        self.declare_parameter("result_topic", "/nexus/execution/result")

        self.tf_buffer = Buffer(cache_time=rclpy.duration.Duration(seconds=10.0))
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.arm_client = ActionClient(self, FollowJointTrajectory, ARM_ACTION)
        self.gripper_client = ActionClient(self, FollowJointTrajectory, GRIPPER_ACTION)
        self.ik_client = self.create_client(GetPositionIK, IK_SERVICE)

        self.latest_scene: Optional[PerceptionResult] = None
        self.latest_joints = None

        self.create_subscription(
            TaskPlan, self.get_parameter("plan_topic").value, self._on_plan, 10
        )
        self.create_subscription(
            PerceptionResult, self.get_parameter("perception_topic").value,
            self._on_perception, 10
        )
        self.create_subscription(
            String, self.get_parameter("joint_state_topic").value, self._on_joints, 10
        )
        self.result_pub = self.create_publisher(
            String, self.get_parameter("result_topic").value, 10
        )

        self._executing = False
        self.get_logger().info("Orchestrator ready. Waiting for TaskPlans...")

    # -------------------- subscriptions -------------------- #
    def _on_perception(self, msg: PerceptionResult) -> None:
        self.latest_scene = msg

    def _on_joints(self, msg) -> None:
        self.latest_joints = msg

    def _on_plan(self, plan: TaskPlan) -> None:
        if self._executing:
            self.get_logger().warn("Already executing; ignoring new plan.")
            return
        self.get_logger().info(f"Received plan {plan.task_id}: {plan.intent}")
        self._execute_plan(plan)

    # -------------------- plan execution -------------------- #
    def _execute_plan(self, plan: TaskPlan) -> None:
        self._executing = True
        self._plan = plan
        self._idx = 0
        self._advance()

    def _advance(self) -> None:
        if self._idx >= len(self._plan.steps):
            self._executing = False
            self._report(True, f"Plan {self._plan.task_id} completed.")
            return
        step = self._plan.steps[self._idx]
        self.get_logger().info(f"Step {self._idx}: {step.action} -> {step.target}")
        if step.action == "move_to":
            self._step_move_to(step.target)
        elif step.action == "grasp":
            self._send_gripper(GRIPPER_CLOSED, f"grasped {step.target}")
        elif step.action == "release":
            self._send_gripper(GRIPPER_OPEN, f"released {step.target}")
        elif step.action == "home":
            self._send_arm(HOME_JOINTS, f"returned home")
        elif step.action == "wait":
            self._report(True, "waiting")
            self._idx += 1
            self._advance()
        else:
            self.get_logger().warn(f"Unknown action: {step.action}")
            self._report(False, f"unknown action {step.action}")
            self._idx += 1
            self._advance()

    # -------------------- actions -------------------- #
    def _step_move_to(self, target: str) -> None:
        if target in ("home",):
            self._send_arm(HOME_JOINTS, "moved home")
            return
        if target in ("ready",):
            self._send_arm(READY_JOINTS, "moved ready")
            return

        pose = self._resolve_target_pose(target)
        if pose is None:
            self._report(False, f"could not resolve target '{target}'")
            self._idx += 1
            self._advance()
            return

        req = GetPositionIK.Request()
        req.ik_request.group_name = "arm"
        req.ik_request.robot_state.joint_state = self.latest_joints
        req.ik_request.pose_stamped = pose
        req.ik_request.timeout = rclpy.duration.Duration(seconds=0.1).to_msg()
        req.ik_request.avoid_collisions = False

        if not self.ik_client.wait_for_service(timeout_sec=5.0):
            self._report(False, "IK service unavailable")
            self._idx += 1
            self._advance()
            return
        fut = self.ik_client.call_async(req)
        fut.add_done_callback(lambda f: self._ik_done(f, f"moved to {target}"))

    def _ik_done(self, future, success_msg: str) -> None:
        try:
            resp = future.result()
        except Exception as exc:  # noqa: BLE001
            self._report(False, f"IK call failed: {exc}")
            self._idx += 1
            self._advance()
            return
        if resp.error_code.val != MoveItErrorCodes.SUCCESS:
            self._report(False, f"IK failed (code {resp.error_code.val})")
            self._idx += 1
            self._advance()
            return
        joints = list(resp.solution.joint_state.position)[:6]
        self._send_arm(joints, success_msg)

    def _send_arm(self, joints: List[float], success_msg: str) -> None:
        if not self.arm_client.wait_for_server(timeout_sec=5.0):
            self._report(False, "arm controller unavailable")
            self._idx += 1
            self._advance()
            return
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ARM_JOINTS
        point = JointTrajectoryPoint()
        point.positions = [float(j) for j in joints]
        point.time_from_start = rclpy.duration.Duration(seconds=4.0).to_msg()
        goal.trajectory.points = [point]
        self.arm_client.send_goal_async(goal).add_done_callback(
            lambda gh_fut: self._goal_response(gh_fut, success_msg)
        )

    def _send_gripper(self, positions: List[float], success_msg: str) -> None:
        if not self.gripper_client.wait_for_server(timeout_sec=5.0):
            self._report(False, "gripper controller unavailable")
            self._idx += 1
            self._advance()
            return
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = GRIPPER_JOINTS
        point = JointTrajectoryPoint()
        point.positions = [float(p) for p in positions]
        point.time_from_start = rclpy.duration.Duration(seconds=1.5).to_msg()
        goal.trajectory.points = [point]
        self.gripper_client.send_goal_async(goal).add_done_callback(
            lambda gh_fut: self._goal_response(gh_fut, success_msg)
        )

    def _goal_response(self, goal_handle_future, success_msg: str) -> None:
        goal_handle = goal_handle_future.result()
        if not goal_handle.accepted:
            self._report(False, "goal rejected")
            self._idx += 1
            self._advance()
            return
        goal_handle.get_result_async().add_done_callback(
            lambda res_fut: self._result_cb(res_fut, success_msg)
        )

    def _result_cb(self, result_future, success_msg: str) -> None:
        result = result_future.result().result
        if result.error_code == 0:  # SUCCESS
            self._report(True, success_msg)
        else:
            self._report(False, f"execution error {result.error_code}")
        self._idx += 1
        self._advance()

    # -------------------- helpers -------------------- #
    def _resolve_target_pose(self, target: str) -> Optional[PoseStamped]:
        if self.latest_scene is None:
            return None
        det = next((o for o in self.latest_scene.objects if o.name == target), None)
        if det is None:
            return None
        try:
            pose_base = self.tf_buffer.transform(
                det.pose, "base_link", timeout=rclpy.duration.Duration(seconds=2.0)
            )
        except TransformException as exc:
            self.get_logger().warn(f"TF transform failed: {exc}")
            return None
        # Approach with gripper pointing down (rotate π about X).
        pose_base.pose.orientation = self._quat_from_rpy(math.pi, 0.0, 0.0)
        pose_base.pose.position.z += 0.02
        return pose_base

    @staticmethod
    def _quat_from_rpy(roll: float, pitch: float, yaw: float) -> Quaternion:
        cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
        cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
        cr, sr = math.cos(roll / 2), math.sin(roll / 2)
        return Quaternion(
            x=sr * cp * cy - cr * sp * sy,
            y=cr * sp * cy + sr * cp * sy,
            z=cr * cp * sy - sr * sp * cy,
            w=cr * cp * cy + sr * sp * sy,
        )

    def _report(self, success: bool, msg: str) -> None:
        prefix = "OK: " if success else "FAIL: "
        self.result_pub.publish(String(data=prefix + msg))
        self.get_logger().info(prefix + msg)


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = OrchestratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
