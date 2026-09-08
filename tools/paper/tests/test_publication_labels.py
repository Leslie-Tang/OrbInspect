"""Keep publication wording readable without changing experiment identities."""
from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publication_labels import PROFILE_LABELS, REPRESENTATIVE_CASE_LEAD, profile_label, objective_label

PAPER = Path(__file__).resolve().parents[3] / 'OrbInspectLatex'


@pytest.mark.parametrize('identifier,expected', PROFILE_LABELS.items())
def test_profile_names(identifier, expected):
    assert profile_label(identifier) == expected


def test_objective_name_and_unknown_identifier_guard():
    assert objective_label('coverage_only80') == r'Coverage-only (80\%)'
    with pytest.raises(KeyError):
        profile_label('unreviewed_experiment_key')


@pytest.mark.parametrize('name', ['required_target_profiles.tex', 'required_target_profile_results.tex',
                                 'required_target_objective_ablation.tex'])
def test_only_table_display_labels_change(name):
    before = (PAPER/'archive/identifier_cleanup_20260908'/name).read_text()
    expected = before
    for key, value in PROFILE_LABELS.items():
        expected = expected.replace(key, value)
    expected = expected.replace('coverage only80', objective_label('coverage_only80'))
    assert (PAPER/'tables'/name).read_text() == expected


def test_representative_case_keeps_selection_and_all_numbers():
    before = (PAPER/'archive/identifier_cleanup_20260908/required_target_case.tex').read_text()
    current = (PAPER/'tables/required_target_case.tex').read_text()
    assert current == REPRESENTATIVE_CASE_LEAD + 'Both routes' + before.split('Both routes', 1)[1]
    manifest = json.loads((PAPER/'data/confirmation/raw/representative_case_manifest.json').read_text())
    assert manifest['scenario_id'] == 'required09_test_000'
    assert r'\texttt' not in current


def test_historical_run_caption_only_changes_display_name():
    before = (PAPER/'archive/identifier_cleanup_20260908/ros_verification_results.tex').read_text()
    expected = before.replace(r'accepted corrected \texttt{validation\_002} task',
                              r'historical ROS~2 validation run')
    assert (PAPER/'sections/ros_verification_results.tex').read_text() == expected
