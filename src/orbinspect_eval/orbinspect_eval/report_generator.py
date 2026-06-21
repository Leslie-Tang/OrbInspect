"""Report helpers for paper experiment summaries."""

from __future__ import annotations

import json
from pathlib import Path


def write_experiment_manifest(
    result_dir: Path,
    scenario: str,
    method: str,
    dynamics_backend: str,
    config_snapshots: list[Path],
) -> Path:
    """Write a lightweight manifest for paper experiment metadata."""
    manifest = {
        'scenario': scenario,
        'method': method,
        'dynamics_backend': dynamics_backend,
        'config_snapshots': [path.name for path in config_snapshots],
    }
    path = result_dir / 'experiment_manifest.json'
    with path.open('w') as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
    return path
