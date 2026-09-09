"""Reproducibility metadata for paper-facing OrbInspect results."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Mapping


RESULT_SCHEMA_VERSION = 'orbinspect-paper-results/v2'
GEOMETRY_QUERY_VERSION = 'full-mesh-bvh/v1'


def collect_result_provenance(
    *,
    result_kind: str,
    config: Mapping[str, object],
    mesh_path: Path | None = None,
    critic_feature_count: int | None = None,
) -> dict[str, object]:
    """Return a deterministic-schema provenance record for one result set."""
    canonical_config = json.dumps(
        config,
        sort_keys=True,
        separators=(',', ':'),
        default=str,
    ).encode('utf-8')
    provenance: dict[str, object] = {
        'result_schema_version': RESULT_SCHEMA_VERSION,
        'geometry_query_version': GEOMETRY_QUERY_VERSION,
        'result_kind': result_kind,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'config_sha256': hashlib.sha256(canonical_config).hexdigest(),
        'git_commit': _git_output('rev-parse', 'HEAD'),
        'git_branch': _git_output('rev-parse', '--abbrev-ref', 'HEAD'),
        'git_dirty': bool(_git_output('status', '--porcelain')),
        'python_version': platform.python_version(),
        'python_implementation': platform.python_implementation(),
        'platform': platform.platform(),
        'executable': Path(sys.executable).name,
    }
    if critic_feature_count is not None:
        provenance['critic_feature_count'] = int(critic_feature_count)
    if mesh_path is not None:
        resolved = mesh_path.resolve()
        if resolved.is_file():
            provenance['mesh'] = {
                'path': mesh_path.as_posix(),
                'size_bytes': resolved.stat().st_size,
                'sha256': _file_sha256(resolved),
            }
        else:
            provenance['mesh'] = {
                'path': mesh_path.as_posix(),
                'missing': True,
            }
    return provenance


def write_result_manifest(
    path: Path,
    provenance: Mapping[str, object],
) -> None:
    """Write provenance as a stable, human-inspectable JSON manifest."""
    path.write_text(
        json.dumps(dict(provenance), indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )


def _git_output(*arguments: str) -> str:
    try:
        completed = subprocess.run(
            ('git', *arguments),
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError):
        return 'unavailable'
    if completed.returncode != 0:
        return 'unavailable'
    return completed.stdout.strip()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
