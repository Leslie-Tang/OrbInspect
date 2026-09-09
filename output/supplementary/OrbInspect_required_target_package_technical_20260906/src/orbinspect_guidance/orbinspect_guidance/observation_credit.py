"""Identity-preserving mission goals and accepted-observation accounting."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ObservationMission:
    """Fixed target universe, weights and explicit terminal requirement."""

    target_weights: Mapping[str, float]
    required_target_ids: frozenset[str] = frozenset()
    goal_mode: str = 'coverage'
    goal_coverage: float = 0.80
    mission_sha256: str = ''

    def __post_init__(self) -> None:
        """Reject unknown requirements and ambiguous coverage denominators."""
        weights = {str(key): float(value) for key, value in self.target_weights.items()}
        if not weights or any(not key for key in weights):
            raise ValueError('mission requires identified targets')
        if any(not math.isfinite(value) or value < 0.0 for value in weights.values()):
            raise ValueError('target weights must be finite and nonnegative')
        if sum(weights.values()) <= 0.0:
            raise ValueError('target weights must have positive total weight')
        if self.goal_mode not in {'coverage', 'required', 'hybrid'}:
            raise ValueError('unknown goal_mode')
        if not math.isfinite(self.goal_coverage) or not 0.0 <= self.goal_coverage <= 1.0:
            raise ValueError('goal_coverage must lie in [0, 1]')
        required = frozenset(self.required_target_ids)
        if required - weights.keys():
            raise ValueError('required target IDs are outside the fixed universe')
        if self.goal_mode in {'required', 'hybrid'} and not required:
            raise ValueError('required and hybrid missions require nonempty target IDs')
        if self.goal_mode in {'coverage', 'hybrid'} and self.goal_coverage <= 0.0:
            raise ValueError('coverage and hybrid missions require a positive coverage goal')
        object.__setattr__(self, 'target_weights', MappingProxyType(weights))
        object.__setattr__(self, 'required_target_ids', required)

    def metadata(self) -> dict[str, object]:
        """Return portable additive metadata for a frozen replay route."""
        return {
            'goal_mode': self.goal_mode,
            'goal_coverage': self.goal_coverage,
            'target_weights': dict(sorted(self.target_weights.items())),
            'required_target_ids': sorted(self.required_target_ids),
            'mission_sha256': self.mission_sha256,
        }


def credit_observation(
    covered: frozenset[str],
    visible: frozenset[str],
    credited: bool,
    mission: ObservationMission,
) -> tuple[frozenset[str], int]:
    """Union only accepted per-observation IDs, with no duplicate credit."""
    if (covered | visible) - mission.target_weights.keys():
        raise ValueError('observation references targets outside the fixed universe')
    accepted = covered | visible if credited else covered
    return accepted, len(accepted - covered)


def coverage_metrics(
    covered: frozenset[str], mission: ObservationMission,
) -> dict[str, object]:
    """Compute all metrics from accepted target identities and fixed denominators."""
    if covered - mission.target_weights.keys():
        raise ValueError('credited targets are outside the fixed universe')
    weighted = sum(mission.target_weights[item] for item in covered) / sum(
        mission.target_weights.values()
    )
    required_covered = covered & mission.required_target_ids
    missing = mission.required_target_ids - covered
    coverage_complete = weighted + 1.0e-12 >= mission.goal_coverage
    required_complete = not missing
    reached = {
        # Preserve the legacy coverage-plus-mandatory-mask conjunction.
        'coverage': coverage_complete and required_complete,
        'required': required_complete,
        'hybrid': coverage_complete and required_complete,
    }[mission.goal_mode]
    return {
        'goal_mode': mission.goal_mode,
        'coverage_ratio': weighted,
        'unweighted_coverage_ratio': len(covered) / len(mission.target_weights),
        'credited_target_count': len(covered),
        'total_target_count': len(mission.target_weights),
        'required_target_count': len(mission.required_target_ids),
        'required_covered_count': len(required_covered),
        'required_coverage_ratio': (
            len(required_covered) / len(mission.required_target_ids)
            if mission.required_target_ids else None
        ),
        'required_targets_complete': required_complete,
        'missing_required_target_ids': sorted(missing),
        'credited_target_ids': sorted(covered),
        'mission_goal_reached': reached,
        'mission_sha256': mission.mission_sha256,
    }


def mission_from_metadata(payload: Mapping[str, object]) -> ObservationMission:
    """Read explicit route metadata without inferring required targets."""
    return ObservationMission(
        target_weights=payload['target_weights'],
        required_target_ids=frozenset(payload.get('required_target_ids', ())),
        goal_mode=str(payload.get('goal_mode', 'coverage')),
        goal_coverage=float(payload.get('goal_coverage', 0.80)),
        mission_sha256=str(payload.get('mission_sha256', '')),
    )


def load_observation_mission(
    result_dir: Path, scenario_id: str, method: str,
    *, goal_mode: str = 'coverage', goal_coverage: float = 0.80,
) -> ObservationMission:
    """Load new self-contained metadata or verified legacy graph/scenario inputs."""
    manifest = json.loads((result_dir / 'manifest.json').read_text())
    routes = [
        item for item in manifest['routes']
        if item['scenario_id'] == scenario_id and item['method'] == method
    ]
    if len(routes) != 1:
        raise ValueError('expected exactly one matching route manifest entry')
    if 'mission' in routes[0]:
        return mission_from_metadata(routes[0]['mission'])
    # Legacy exports preserved identities in viewpoints but kept the universe
    # and scenario weights in their hash-pinned source archive.
    source = Path(manifest['source_result_root'])
    candidates = [source, result_dir.parent / source.name]
    for parent in result_dir.resolve().parents:
        candidates.append(parent / 'data' / 'results' / source.name)
    source = next((path for path in candidates if (path / 'raw/hcw_graph.json').is_file()), source)
    payloads = {}
    for filename in ('hcw_graph.json', 'scenarios.json'):
        path = source / 'raw' / filename
        if not path.is_file():
            raise FileNotFoundError(
                f'legacy replay needs its source {filename}; re-export with mission metadata'
            )
        expected = manifest.get('source_files_sha256', {}).get(filename)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not expected or actual != expected:
            raise ValueError(f'legacy source hash mismatch: {filename}')
        payloads[filename] = json.loads(path.read_text())
    scenarios = [
        item for item in payloads['scenarios.json']
        if item['scenario_id'] == scenario_id
    ]
    if len(scenarios) != 1:
        raise ValueError('expected exactly one matching source scenario')
    scenario = scenarios[0]
    ids = payloads['hcw_graph.json']['target_ids']
    weights = scenario['target_weights']
    if len(ids) != len(weights):
        raise ValueError('target IDs and weights have different lengths')
    return ObservationMission(
        target_weights=dict(zip(ids, weights)),
        goal_mode=goal_mode,
        goal_coverage=goal_coverage,
    )
