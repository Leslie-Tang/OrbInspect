"""Temporal evidence selection must fail instead of clamping absent frames."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_required_target_camera_snapshot import nearest_index, named_chaser_pose


def test_nearest_record_is_local_and_requires_temporal_bracketing():
    assert nearest_index([1, 2, 3], 1.8) == 1
    assert nearest_index([1, 2, 3], 2.5) == 1
    assert nearest_index([1, 2, 3], 3) == 2
    with pytest.raises(ValueError, match='outside'):
        nearest_index([1, 2, 3], 0.9)
    with pytest.raises(ValueError, match='outside'):
        nearest_index([1, 2, 3], 3.1)


def test_empty_startup_scenes_do_not_create_a_pose_and_duplicate_chasers_fail():
    assert named_chaser_pose({'header': {'stamp': {}}}) is None
    assert named_chaser_pose({'pose': [{'name': 'iss'}]}) is None
    chaser = {'name': 'chaser', 'position': {'x': 1}, 'orientation': {'w': 1}}
    assert named_chaser_pose({'pose': [chaser]}) == chaser
    with pytest.raises(ValueError, match='Multiple named'):
        named_chaser_pose({'pose': [chaser, chaser]})
