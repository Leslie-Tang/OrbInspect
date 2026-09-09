"""ROS status node for the safety-shielded graph ADP planner."""

from __future__ import annotations

from collections.abc import Sequence
import json

from orbinspect_guidance.advanced_safe_planner import AdvancedPlannerConfig
from orbinspect_guidance.advanced_safe_planner import AdvancedSafePlanner
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class AdvancedSafePlannerNode(Node):
    """Publish readiness and configuration for the graph ADP core."""

    def __init__(self) -> None:
        super().__init__('advanced_safe_planner_node')
        self.declare_parameter('method', 'safe_graph_adp')
        self.declare_parameter('horizon_steps', 36)
        self.declare_parameter('time_step', 90.0)
        self.declare_parameter('safety_margin', 2.0)
        self.declare_parameter('goal_coverage', 0.98)
        self.declare_parameter('branch_width', 8)
        self.declare_parameter('candidate_pool_width', 24)
        self.declare_parameter('lookahead_depth', 3)
        self.declare_parameter('training_episodes', 80)
        self.declare_parameter('learning_rate', 0.035)
        self.declare_parameter('exploration_rate', 0.25)
        self.declare_parameter('terminal_penalty', 500.0)
        self.declare_parameter('action_cost', 0.05)
        self.declare_parameter('cost_scale', 50.0)
        self.declare_parameter('random_seed', 7)
        self.declare_parameter('min_new_target_count', 1)
        self.declare_parameter('oracle_node_limit', 14)
        self.declare_parameter('reference_improvement_passes', 4)
        self.declare_parameter('enable_critic', True)
        self.declare_parameter('enable_rollout', True)
        self.declare_parameter('enable_reference_safeguard', True)
        self.declare_parameter('publish_rate', 1.0)
        config = AdvancedPlannerConfig(
            method=str(self.get_parameter('method').value),
            horizon_steps=int(self.get_parameter('horizon_steps').value),
            time_step=float(self.get_parameter('time_step').value),
            safety_margin=float(self.get_parameter('safety_margin').value),
            goal_coverage=float(self.get_parameter('goal_coverage').value),
            branch_width=int(self.get_parameter('branch_width').value),
            candidate_pool_width=int(
                self.get_parameter('candidate_pool_width').value
            ),
            lookahead_depth=int(self.get_parameter('lookahead_depth').value),
            training_episodes=int(self.get_parameter('training_episodes').value),
            learning_rate=float(self.get_parameter('learning_rate').value),
            exploration_rate=float(self.get_parameter('exploration_rate').value),
            terminal_penalty=float(self.get_parameter('terminal_penalty').value),
            action_cost=float(self.get_parameter('action_cost').value),
            cost_scale=float(self.get_parameter('cost_scale').value),
            random_seed=int(self.get_parameter('random_seed').value),
            min_new_target_count=int(
                self.get_parameter('min_new_target_count').value
            ),
            oracle_node_limit=int(
                self.get_parameter('oracle_node_limit').value
            ),
            reference_improvement_passes=int(
                self.get_parameter('reference_improvement_passes').value
            ),
            enable_critic=bool(self.get_parameter('enable_critic').value),
            enable_rollout=bool(self.get_parameter('enable_rollout').value),
            enable_reference_safeguard=bool(
                self.get_parameter('enable_reference_safeguard').value
            ),
        )
        self.planner = AdvancedSafePlanner(config)
        self.status_pub = self.create_publisher(String, '/advanced_planner/status', 10)
        publish_rate = float(self.get_parameter('publish_rate').value)
        if publish_rate <= 0.0:
            raise ValueError('publish_rate must be positive')
        self.create_timer(1.0 / publish_rate, self._publish_status)

    def _publish_status(self) -> None:
        status = {
            'time': self.get_clock().now().nanoseconds * 1.0e-9,
            'state': 'ready' if self.planner.available else 'unavailable',
            'available': self.planner.available,
            'method': self.planner.config.method,
            'critic_enabled': self.planner.config.enable_critic,
            'rollout_enabled': self.planner.config.enable_rollout,
            'safeguard_enabled': (
                self.planner.config.enable_reference_safeguard
            ),
            'local_improvement_enabled': (
                self.planner.config.enable_reference_safeguard
                and self.planner.config.reference_improvement_passes > 0
            ),
            'message': (
                'graph ADP core is available; offline experiment supplies '
                'the candidate graph and HCW safety shield'
            ),
        }
        self.status_pub.publish(String(data=json.dumps(status, sort_keys=True)))


def main(args: Sequence[str] | None = None) -> None:
    rclpy.init(args=args)
    node = AdvancedSafePlannerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        finally:
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == '__main__':
    main()
