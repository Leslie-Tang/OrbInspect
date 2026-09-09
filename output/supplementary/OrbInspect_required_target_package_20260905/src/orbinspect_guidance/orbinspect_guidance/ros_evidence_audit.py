"""Audit one recorded ROS run against the full ISS mesh and frozen gates."""

from __future__ import annotations

import argparse
import csv
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

from orbinspect_guidance.offline_coverage_planner import IssMeshGeometry


DEFAULT_MESH = Path(
    'src/orbinspect_description/models/iss_real/meshes/ISS_stationary.glb'
)
MESH_SCALE = 1.065
MESH_SHA256 = '26dba905b4b7555edbcb0c5f5a61b5c18659f5166076ab27dbb0e64025759fca'


def audit_run(
    result_dir: Path,
    mesh_path: Path = DEFAULT_MESH,
    safety_margin: float = 2.0,
    max_acceleration: float = 0.060,
    vehicle_radius: float = 0.80,
) -> dict[str, object]:
    """Audit recorded samples, terminal verification, and swept-body clearance."""
    if safety_margin <= 0.0:
        raise ValueError('safety_margin must be positive')
    if vehicle_radius < 0.0:
        raise ValueError('vehicle_radius must be non-negative')
    result_dir = result_dir.resolve()
    mesh_path = _resolve_path(mesh_path)
    if _sha256(mesh_path) != MESH_SHA256:
        raise RuntimeError(f'ISS mesh hash mismatch: {mesh_path}')
    trajectory = _read_csv(result_dir / 'raw' / 'trajectory.csv')
    control = _read_csv(result_dir / 'raw' / 'control.csv')
    if len(trajectory) < 2:
        raise ValueError('executed trajectory must contain at least two samples')
    geometry = _load_geometry(str(mesh_path))
    points = [
        tuple(float(row[name]) for name in ('rx', 'ry', 'rz'))
        for row in trajectory
    ]
    distances = [geometry.surface_distance(point) for point in points]
    crossing_indices = [
        index
        for index, (start, end) in enumerate(zip(points, points[1:]))
        if geometry.segment_crosses_surface(start, end)
    ]
    segment_lengths = [
        math.sqrt(sum((end[axis] - start[axis]) ** 2 for axis in range(3)))
        for start, end in zip(points, points[1:])
    ]
    acceleration_norms = [
        math.sqrt(sum(float(row[name]) ** 2 for name in ('ax_safe', 'ay_safe', 'az_safe')))
        for row in control
    ]
    summary_path = result_dir / 'summary.json'
    summary = json.loads(summary_path.read_text()) if summary_path.is_file() else {}
    verification = summary.get('verification', {})
    reference_stream = summary.get('reference_stream', {})
    min_distance = min(distances)
    maximum_segment_length = max(segment_lengths, default=0.0)
    # Distance to a closed mesh is 1-Lipschitz. Every point on a segment is at
    # most half that segment's length from an endpoint, so this is a rigorous
    # lower bound for continuous centerline clearance between recorded samples.
    continuous_distance_lower_bound = min(
        min(distances[index], distances[index + 1])
        - 0.5 * segment_lengths[index]
        for index in range(len(segment_lengths))
    )
    body_distance_lower_bound = continuous_distance_lower_bound - vehicle_radius
    peak_acceleration = max(acceleration_norms, default=0.0)
    gates = {
        'terminal_verification': bool(verification.get('success', False)),
        'reference_stream_completion': bool(reference_stream.get('passed', False)),
        'trajectory_samples_present': len(trajectory) >= 2,
        'control_samples_present': bool(control),
        'no_full_mesh_surface_crossing': not crossing_indices,
        'full_mesh_safety_margin': min_distance + 1.0e-9 >= safety_margin,
        'finite_body_safety_margin': (
            body_distance_lower_bound + 1.0e-9 >= safety_margin
        ),
        'acceleration_limit': peak_acceleration <= max_acceleration + 1.0e-9,
    }
    payload = {
        'schema_version': 'orbinspect-ros-evidence-audit/v2',
        'result_dir': str(result_dir),
        'mesh_path': str(mesh_path),
        'mesh_sha256': MESH_SHA256,
        'mesh_scale': MESH_SCALE,
        'mesh_transform': 'full_gltf_scene_hierarchy_then_sdf_pitch_90_scale',
        'safety_margin_m': safety_margin,
        'vehicle_bounding_radius_m': vehicle_radius,
        'max_acceleration_mps2': max_acceleration,
        'trajectory_samples': len(trajectory),
        'control_samples': len(control),
        'minimum_mesh_distance_m': min_distance,
        'minimum_mesh_clearance_m': min_distance - safety_margin,
        'maximum_trajectory_segment_length_m': maximum_segment_length,
        'minimum_continuous_center_distance_lower_bound_m': (
            continuous_distance_lower_bound
        ),
        'minimum_body_distance_lower_bound_m': body_distance_lower_bound,
        'minimum_body_clearance_m': body_distance_lower_bound - safety_margin,
        'surface_crossing_segment_indices': crossing_indices,
        'peak_safe_acceleration_mps2': peak_acceleration,
        'verification': verification,
        'reference_stream': reference_stream,
        'gates': gates,
        'passed': all(gates.values()),
    }
    audit_path = result_dir / 'mesh_execution_audit.json'
    audit_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    if isinstance(summary, dict):
        summary['mesh_execution_audit'] = payload
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
        _append_markdown_audit(result_dir / 'summary.md', payload)
    return payload


def _append_markdown_audit(
    path: Path,
    payload: dict[str, object],
) -> None:
    """Add an idempotent human-readable full-mesh audit section."""
    marker = '## Full-mesh execution audit'
    existing = path.read_text(encoding='utf-8') if path.is_file() else ''
    prefix = existing.split(marker, 1)[0].rstrip()
    crossings = payload['surface_crossing_segment_indices']
    lines = [
        prefix,
        '',
        marker,
        '',
        f"- Audit passed: {payload['passed']}",
        (
            '- Vehicle bounding radius: '
            f"{float(payload['vehicle_bounding_radius_m']):.6f} m"
        ),
        f'- Swept mesh crossings: {len(crossings)}',
        (
            '- Minimum finite-body clearance above the required margin: '
            f"{float(payload['minimum_body_clearance_m']):.6f} m"
        ),
    ]
    path.write_text('\n'.join(lines).lstrip() + '\n', encoding='utf-8')


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=2)
def _load_geometry(path_text: str) -> IssMeshGeometry:
    return IssMeshGeometry.load(Path(path_text), MESH_SCALE, 0)


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    workspace_path = Path(__file__).resolve().parents[3] / path
    return workspace_path.resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('result_dir', type=Path)
    parser.add_argument('--mesh-path', type=Path, default=DEFAULT_MESH)
    parser.add_argument('--safety-margin', type=float, default=2.0)
    parser.add_argument('--max-acceleration', type=float, default=0.060)
    parser.add_argument('--vehicle-radius', type=float, default=0.80)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the evidence audit."""
    args = parse_args(argv)
    payload = audit_run(
        args.result_dir,
        args.mesh_path,
        args.safety_margin,
        args.max_acceleration,
        args.vehicle_radius,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
