import math
from pathlib import Path

from orbinspect_guidance.planned_trajectory_replay_node import _build_standoff_trajectory
from orbinspect_guidance.planned_trajectory_replay_node import _continuous_attitudes
from orbinspect_guidance.planned_trajectory_replay_node import _fov_corners
from orbinspect_guidance.planned_trajectory_replay_node import _finite_difference_acceleration
from orbinspect_guidance.planned_trajectory_replay_node import _load_attitudes
from orbinspect_guidance.planned_trajectory_replay_node import _load_trajectory
from orbinspect_guidance.planned_trajectory_replay_node import _load_viewpoints
from orbinspect_guidance.planned_trajectory_replay_node import _make_reference_state
from orbinspect_guidance.planned_trajectory_replay_node import _segment_ratio
from orbinspect_guidance.planned_trajectory_replay_node import _slerp
from orbinspect_guidance.planned_trajectory_replay_node import PlannedTrajectoryReplayNode
import pytest


def test_loads_planned_replay_csv_files(tmp_path: Path) -> None:
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir()
    (raw_dir / 'trajectory.csv').write_text(
        'method,time,rx,ry,rz,vx,vy,vz,ax,ay,az\n'
        'set_cover_cw_tour,2.0,1.0,2.0,3.0,0.1,0.2,0.3,0,0,0\n'
        'baseline,2.0,9.0,9.0,9.0,0,0,0,0,0,0\n'
    )
    (raw_dir / 'attitude.csv').write_text(
        'method,time,boresight_x,boresight_y,boresight_z,'
        'yaw_rad,pitch_rad,qx,qy,qz,qw\n'
        'set_cover_cw_tour,2.0,1.0,0.0,0.0,0,0,0,0,0,1\n'
    )
    (raw_dir / 'viewpoints.csv').write_text(
        'method,sequence,candidate_id,viewpoint_x,viewpoint_y,viewpoint_z,'
        'boresight_x,boresight_y,boresight_z,yaw_rad,pitch_rad,'
        'qx,qy,qz,qw,new_target_count,cumulative_coverage\n'
        'set_cover_cw_tour,0,cand,1.0,2.0,3.0,0.0,1.0,0.0,0,0,0,0,0,1,1,0.1\n'
    )

    trajectory = _load_trajectory(tmp_path, 'set_cover_cw_tour')
    attitudes = _load_attitudes(tmp_path, 'set_cover_cw_tour')
    viewpoints = _load_viewpoints(tmp_path, 'set_cover_cw_tour')

    assert len(trajectory) == 1
    assert trajectory[0]['rx'] == 1.0
    assert attitudes[2.0]['boresight_x'] == 1.0
    quaternion_norm = sum(
        attitudes[2.0][key] ** 2
        for key in ('qx', 'qy', 'qz', 'qw')
    )
    assert abs(quaternion_norm - 1.0) < 1.0e-9
    assert viewpoints[0]['boresight_y'] == 1.0


def test_fov_corners_form_four_far_plane_points() -> None:
    corners = _fov_corners(
        origin=(0.0, 0.0, 0.0),
        boresight=(1.0, 0.0, 0.0),
        horizontal_fov_deg=70.0,
        vertical_fov_deg=50.0,
        fov_range=25.0,
    )

    assert len(corners) == 4
    assert all(corner[0] > 20.0 for corner in corners)


def test_continuous_attitudes_remove_boresight_roll_flip() -> None:
    rows = [
        {
            'time': 466.0,
            'boresight_x': -0.034,
            'boresight_y': -0.307,
            'boresight_z': -0.951,
        },
        {
            'time': 468.0,
            'boresight_x': -0.036,
            'boresight_y': -0.317,
            'boresight_z': -0.948,
        },
        {
            'time': 470.0,
            'boresight_x': -0.038,
            'boresight_y': -0.325,
            'boresight_z': -0.945,
        },
    ]

    attitudes = _continuous_attitudes(rows)
    quaternions = [
        tuple(attitudes[row['time']][key] for key in ('qx', 'qy', 'qz', 'qw'))
        for row in rows
    ]
    max_step = max(
        2.0 * math.acos(min(1.0, abs(sum(a * b for a, b in zip(q0, q1)))))
        for q0, q1 in zip(quaternions, quaternions[1:])
    )

    assert math.degrees(max_step) < 5.0


def test_station_mesh_marker_uses_nasa_iss_resource() -> None:
    node = PlannedTrajectoryReplayNode.__new__(PlannedTrajectoryReplayNode)
    node.frame_id = 'lvlh'
    node.station_mesh_resource = (
        'package://orbinspect_description/models/iss_real/meshes/ISS_stationary_rviz.stl'
    )
    node.station_mesh_scale = 1.065

    marker = node._make_station_mesh_marker(stamp=None)

    assert marker.header.frame_id == 'lvlh'
    assert marker.mesh_resource.endswith('ISS_stationary_rviz.stl')
    assert marker.scale.x == 1.065
    assert marker.pose.orientation.y > 0.7
    assert not marker.mesh_use_embedded_materials


def test_interpolation_helpers_are_smooth_and_unit_length() -> None:
    assert _segment_ratio(2.0, 4.0, 3.0) == 0.5
    quaternion = _slerp(
        (0.0, 0.0, 0.0, 1.0),
        (0.0, 0.0, 1.0, 0.0),
        0.5,
    )

    assert abs(sum(value * value for value in quaternion) - 1.0) < 1.0e-9
    assert quaternion[2] > 0.0
    assert quaternion[3] > 0.0


def test_reference_state_encodes_velocity_and_feedforward_acceleration() -> None:
    sample = {
        'time': 2.0,
        'rx': 1.0,
        'ry': 2.0,
        'rz': 3.0,
        'vx': 0.1,
        'vy': 0.2,
        'vz': 0.3,
    }
    attitude = {
        'boresight_x': 1.0,
        'boresight_y': 0.0,
        'boresight_z': 0.0,
        'qx': 0.0,
        'qy': 0.0,
        'qz': 0.0,
        'qw': 1.0,
    }

    msg = _make_reference_state(None, 'lvlh', 'chaser_body', sample, attitude, (4.0, 5.0, 6.0))

    assert msg.pose.pose.position.x == 1.0
    assert msg.twist.twist.linear.y == 0.2
    assert msg.twist.twist.angular.z == 6.0


def test_finite_difference_acceleration_from_reference_samples() -> None:
    acceleration = _finite_difference_acceleration(
        {'time': 1.0, 'vx': 1.0, 'vy': 2.0, 'vz': 3.0},
        {'time': 3.0, 'vx': 5.0, 'vy': 0.0, 'vz': 7.0},
    )

    assert acceleration == pytest.approx((2.0, -1.0, 2.0))


def test_standoff_trajectory_projects_between_viewpoints_on_safe_shell() -> None:
    trajectory = _build_standoff_trajectory(
        csv_trajectory=[{
            'time': 0.0,
            'rx': 0.0,
            'ry': -35.0,
            'rz': 10.0,
            'vx': 0.0,
            'vy': 0.0,
            'vz': 0.0,
        }],
        viewpoints=[{
            'viewpoint_x': 5.0,
            'viewpoint_y': 10.0,
            'viewpoint_z': 50.0,
            'boresight_x': 0.0,
            'boresight_y': -0.2,
            'boresight_z': -0.98,
        }],
        safe_shell_radius=110.0,
        standoff_distance=35.0,
        sample_spacing=2.0,
    )

    assert trajectory
    max_radius = max(
        math.sqrt(sample['rx']**2 + sample['ry']**2 + sample['rz']**2)
        for sample in trajectory
    )
    assert max_radius >= 100.0


def test_rviz_iss_mesh_matches_nasa_glb_bounds() -> None:
    trimesh = pytest.importorskip('trimesh')
    root = Path(__file__).resolve().parents[3]
    glb = root / 'src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb'
    stl = root / 'src/orbinspect_description/models/iss_real/meshes/ISS_stationary_rviz.stl'
    glb_mesh = trimesh.load(glb, force='scene').to_geometry()
    stl_mesh = trimesh.load(stl, force='mesh')

    for glb_extent, stl_extent in zip(glb_mesh.extents, stl_mesh.extents):
        assert abs(glb_extent - stl_extent) < 1.0e-4
