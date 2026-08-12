from geometry_msgs.msg import PointStamped
from nav_msgs.msg import Odometry
from orbinspect_control.controller_node import ControllerNode


def test_full_state_reference_takes_precedence_over_legacy_point() -> None:
    node = ControllerNode.__new__(ControllerNode)
    node.received_reference_state = False
    node.reference = (0.0, 0.0, 0.0)
    node.reference_velocity = (0.0, 0.0, 0.0)
    node.feedforward_acceleration = (0.0, 0.0, 0.0)
    state = Odometry()
    state.pose.pose.position.x = 1.0
    state.twist.twist.linear.y = 2.0
    state.twist.twist.angular.z = 3.0
    node._reference_state_callback(state)
    legacy = PointStamped()
    legacy.point.x = 9.0

    node._reference_callback(legacy)

    assert node.reference == (1.0, 0.0, 0.0)
    assert node.reference_velocity == (0.0, 2.0, 0.0)
    assert node.feedforward_acceleration == (0.0, 0.0, 3.0)
