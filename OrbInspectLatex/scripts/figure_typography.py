"""Shared typography at the final IEEE TAES single-column print dimensions."""
from pathlib import Path

from matplotlib import font_manager

# IEEEtaes: (41 pc text width - 12 pt gutter) / 2 = 240 TeX pt.
# Matplotlib/PDF use 72 points per inch; TeX uses 72.27.
COLUMN_WIDTH_PT = 240 * 72 / 72.27
TEXT_PT = 8.0


def register_fonts(directory: Path | None) -> None:
    """Register an optional author-supplied Arial directory for this process."""
    if directory is not None:
        for path in sorted(directory.glob('*.[tT][tT][fF]')):
            font_manager.fontManager.addfont(str(path))
    try:
        font_manager.findfont(font_manager.FontProperties(family='Arial'), fallback_to_default=False)
    except ValueError as exc:
        raise RuntimeError('Arial is required for the approved layout; install it or pass --font-dir.') from exc
