import csv
import json
from pathlib import Path

from orbinspect_guidance import ros_evidence_audit
import pytest


class _FakeGeometry:
    def surface_distance(self, point):
        return 4.0

    def segment_crosses_surface(self, start, end):
        return False


class _FakeLoader:
    @staticmethod
    def load(path, scale, limit):
        return _FakeGeometry()


def test_audit_run_combines_terminal_mesh_and_control_gates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw = tmp_path / 'raw'
    raw.mkdir()
    mesh = tmp_path / 'iss.glb'
    mesh.write_bytes(b'mesh')
    _write_csv(
        raw / 'trajectory.csv',
        ('rx', 'ry', 'rz'),
        ({'rx': 0, 'ry': 0, 'rz': 0}, {'rx': 1, 'ry': 0, 'rz': 0}),
    )
    _write_csv(
        raw / 'control.csv',
        ('ax_safe', 'ay_safe', 'az_safe'),
        ({'ax_safe': 0.01, 'ay_safe': 0, 'az_safe': 0},),
    )
    (tmp_path / 'summary.json').write_text(json.dumps({
        'verification': {'success': True, 'reason': 'all_execution_gates_passed'},
        'reference_stream': {'passed': True},
    }))
    monkeypatch.setattr(ros_evidence_audit, 'IssMeshGeometry', _FakeLoader)
    monkeypatch.setattr(
        ros_evidence_audit,
        '_sha256',
        lambda path: ros_evidence_audit.MESH_SHA256,
    )

    result = ros_evidence_audit.audit_run(tmp_path, mesh)

    assert result['passed']
    assert result['minimum_mesh_clearance_m'] == 2.0
    assert result['minimum_body_clearance_m'] == pytest.approx(0.70)
    assert result['gates']['finite_body_safety_margin']
    assert (tmp_path / 'mesh_execution_audit.json').is_file()
    merged = json.loads((tmp_path / 'summary.json').read_text())
    assert merged['mesh_execution_audit']['passed']
    markdown = (tmp_path / 'summary.md').read_text()
    assert 'Audit passed: True' in markdown
    assert 'Swept mesh crossings: 0' in markdown


def _write_csv(path: Path, columns, rows) -> None:
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
