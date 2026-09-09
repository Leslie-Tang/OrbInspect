"""Physical and provenance checks for the derived settling schedule."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from add_ros_terminal_dwell import add_dwell
from orbinspect_dynamics.hcw_dynamics import HCWDynamics


def test_stationary_hold_preserves_targets_transfers_and_source(tmp_path):
    source = (Path(__file__).resolve().parents[3] /
              'OrbInspectLatex/data/required_target_ros/'
              '20260909_031355_required09_adp_closed_loop/config_snapshot/replay_inputs')
    before = hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest()
    out = add_dwell(source, tmp_path/'derived', 60, 0.00113137)
    original = json.loads((source/'manifest.json').read_text())
    derived = json.loads((out/'manifest.json').read_text())
    assert derived['routes'][0]['mission'] == original['routes'][0]['mission']
    assert derived['routes'][0]['route_node_ids'] == original['routes'][0]['route_node_ids']
    assert derived['routes'][0]['duration_s'] == 1350
    assert not derived['routes'][0]['metrics_archived']
    assert hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest() == before
    rows = list(csv.DictReader((out/'raw/trajectory.csv').open()))
    assert len(rows) == 450
    assert all(float(b['time']) > float(a['time']) for a, b in zip(rows, rows[1:]))
    frozen = list(csv.DictReader((source/'raw/trajectory.csv').open()))
    for row in frozen:
        match = next(r for r in rows if r['action'] == row['action'] and r['sample'] == row['sample'])
        assert all(match[k] == row[k] for k in ('rx', 'ry', 'rz', 'vx', 'vy', 'vz', 'ax', 'ay', 'az'))
    model = HCWDynamics(0.00113137)
    for row in rows:
        if int(row['sample']) < 30:
            continue
        state = [float(row[k]) for k in ('rx', 'ry', 'rz', 'vx', 'vy', 'vz')]
        control = [float(row[k]) for k in ('ax', 'ay', 'az')]
        np.testing.assert_allclose(model.derivative(state, control), 0, atol=1e-15)
    views = list(csv.DictReader((out/'raw/viewpoints.csv').open()))
    assert [float(r['time']) for r in views] == list(range(150, 1351, 150))
    for name, digest in derived['output_files_sha256'].items():
        assert hashlib.sha256((out/'raw'/name).read_bytes()).hexdigest() == digest


def test_dwell_cannot_overwrite_or_use_off_grid_time(tmp_path):
    with pytest.raises(FileExistsError):
        add_dwell(tmp_path, tmp_path, 60, 0.001)
