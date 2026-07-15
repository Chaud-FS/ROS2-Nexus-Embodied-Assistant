"""Unit tests for the orchestrator node (pure helpers, no ROS runtime)."""
import math

from nexus_orchestrator.orchestrator_node import OrchestratorNode


def test_quat_from_rpy_identity():
    q = OrchestratorNode._quat_from_rpy(0.0, 0.0, 0.0)
    assert (q.x, q.y, q.z, q.w) == (0.0, 0.0, 0.0, 1.0)


def test_quat_from_rpy_pi_about_x():
    q = OrchestratorNode._quat_from_rpy(math.pi, 0.0, 0.0)
    # 180 deg rotation about X -> x ~ 1, w ~ 0
    assert abs(q.x - 1.0) < 1e-6
    assert abs(q.w) < 1e-6


def test_quat_from_rpy_pi_about_z():
    q = OrchestratorNode._quat_from_rpy(0.0, 0.0, math.pi)
    assert abs(q.z - 1.0) < 1e-6
    assert abs(q.w) < 1e-6


def test_module_importable():
    assert OrchestratorNode is not None
