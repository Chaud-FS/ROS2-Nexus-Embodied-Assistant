"""Qwen-VL perception node.

Subscribes to the gripper camera stream, and on demand (service call or timer)
runs the Qwen-VL model to detect objects. Bounding boxes are projected into a
camera-frame 3D point at a nominal depth and published as a PerceptionResult.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import rclpy
from cv_bridge import CvBridge
from nexus_interfaces.msg import DetectedObject, PerceptionResult
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_srvs.srv import Trigger

from .qwen_vl_client import QwenVLClient


class QwenVLNode(Node):
    def __init__(self) -> None:
        super().__init__("qwen_vl_node")

        self.declare_parameter("api_key", "")
        self.declare_parameter("model", "qwen-vl-max")
        self.declare_parameter("base_url", "")
        self.declare_parameter("image_topic", "/nexus/camera/rgb/image_raw")
        self.declare_parameter("camera_info_topic", "/nexus/camera/rgb/camera_info")
        self.declare_parameter("result_topic", "/nexus/perception/result")
        self.declare_parameter("trigger_service", "/nexus/perception/trigger")
        self.declare_parameter("nominal_depth", 0.55)
        self.declare_parameter("timer_period", 0.0)  # 0 -> manual only

        api_key = self.get_parameter("api_key").value or os.environ.get(
            "DASHSCOPE_API_KEY"
        ) or os.environ.get("OPENAI_API_KEY", "")
        model = self.get_parameter("model").value
        base_url = self.get_parameter("base_url").value or None
        image_topic = self.get_parameter("image_topic").value
        info_topic = self.get_parameter("camera_info_topic").value
        result_topic = self.get_parameter("result_topic").value
        trigger = self.get_parameter("trigger_service").value
        self.nominal_depth = float(self.get_parameter("nominal_depth").value)

        self.client = QwenVLClient(api_key, model, base_url)
        self.bridge = CvBridge()

        self.latest_image: Optional[np.ndarray] = None
        self.camera_info: Optional[CameraInfo] = None

        self.sub_img = self.create_subscription(
            Image, image_topic, self._img_cb, 10
        )
        self.sub_info = self.create_subscription(
            CameraInfo, info_topic, self._info_cb, 10
        )
        self.pub = self.create_publisher(PerceptionResult, result_topic, 10)
        self.srv = self.create_service(Trigger, trigger, self._trigger_cb)

        period = float(self.get_parameter("timer_period").value)
        if period > 0.0:
            self.create_timer(period, self._analyze)

        self.get_logger().info(
            f"Qwen-VL perception ready (model={model}, key_set={bool(api_key)}). "
            f"Call service '{trigger}' to analyse the scene."
        )

    # ---------------- callbacks ---------------- #
    def _img_cb(self, msg: Image) -> None:
        try:
            self.latest_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f"Image convert failed: {exc}")

    def _info_cb(self, msg: CameraInfo) -> None:
        self.camera_info = msg

    def _trigger_cb(self, _req: Trigger.Request, resp: Trigger.Response):
        result = self._analyze()
        resp.success = result is not None
        resp.message = result.scene_description if result else "no image available"
        return resp

    # ---------------- core ---------------- #
    def _analyze(self) -> Optional[PerceptionResult]:
        if self.latest_image is None:
            self.get_logger().warn("No image yet, skipping analysis.")
            return None

        from PIL import Image as PILImage

        pil = PILImage.fromarray(np.ascontiguousarray(self.latest_image))
        data = self.client.analyze(pil)

        result = PerceptionResult()
        result.scene_description = data.get("scene_description", "")
        for obj in data.get("objects", []):
            det = DetectedObject()
            det.name = str(obj.get("name", "unknown"))
            det.confidence = float(obj.get("confidence", 0.0))
            bbox = obj.get("bbox", [0, 0, 0, 0])
            det.bbox_min.x, det.bbox_min.y = float(bbox[0]), float(bbox[1])
            det.bbox_max.x, det.bbox_max.y = float(bbox[2]), float(bbox[3])
            cx = (det.bbox_min.x + det.bbox_max.x) / 2.0
            cy = (det.bbox_min.y + det.bbox_max.y) / 2.0
            det.pose = self._project(cx, cy)
            result.objects.append(det)

        self.pub.publish(result)
        self.get_logger().info(
            f"Perception: {result.scene_description} ({len(result.objects)} objects)"
        )
        return result

    def _project(self, cx: float, cy: float):
        from geometry_msgs.msg import PoseStamped

        pose = PoseStamped()
        pose.header.frame_id = "camera_link"
        pose.header.stamp = self.get_clock().now().to_msg()
        if self.camera_info is not None:
            k = self.camera_info.k
            fx, fy = k[0], k[4]
            cx0, cy0 = k[2], k[5]
        else:
            fx = fy = 480.0
            cx0 = cy0 = 320.0
        z = self.nominal_depth
        pose.pose.position.x = (cx - cx0) / fx * z
        pose.pose.position.y = (cy - cy0) / fy * z
        pose.pose.position.z = z
        pose.pose.orientation.w = 1.0
        return pose


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = QwenVLNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
