"""Helpers for creating paper experiment result directories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import time


@dataclass(frozen=True)
class ExperimentPaths:
    """Paper experiment directory layout."""

    result_dir: Path
    raw_dir: Path
    config_snapshot_dir: Path
    rosbag_dir: Path
    figures_dir: Path
    videos_dir: Path


def create_experiment_layout(
    result_root: str = 'data/results',
    run_id: str = '',
) -> ExperimentPaths:
    """Create the required paper experiment output directory structure."""
    root = Path(result_root).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    run_name = run_id if run_id else time.strftime('%Y%m%d_%H%M%S')
    result_dir = root / run_name
    counter = 1
    while result_dir.exists():
        result_dir = root / f'{run_name}_{counter:02d}'
        counter += 1
    raw_dir = result_dir / 'raw'
    config_snapshot_dir = result_dir / 'config_snapshot'
    rosbag_dir = result_dir / 'rosbag'
    figures_dir = result_dir / 'figures'
    videos_dir = result_dir / 'videos'
    for path in (raw_dir, config_snapshot_dir, rosbag_dir, figures_dir, videos_dir):
        path.mkdir(parents=True, exist_ok=True)
    return ExperimentPaths(
        result_dir=result_dir,
        raw_dir=raw_dir,
        config_snapshot_dir=config_snapshot_dir,
        rosbag_dir=rosbag_dir,
        figures_dir=figures_dir,
        videos_dir=videos_dir,
    )


def snapshot_configs(paths: ExperimentPaths, config_paths: list[str]) -> list[Path]:
    """Copy readable config files into the experiment snapshot directory."""
    copied = []
    for path_text in config_paths:
        source = Path(path_text)
        if not source.exists() or not source.is_file():
            continue
        destination = paths.config_snapshot_dir / source.name
        shutil.copy2(source, destination)
        copied.append(destination)
    return copied
