"""Route regenerated manuscript assets into the numbered figure folders."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT/'OrbInspectLatex/figures'


def figure_directory(stem: str) -> Path:
    """Keep legacy architecture outputs separate from approved Figure 2."""
    families = {
        'adp_depth_tradeoff_': 'fig03_depth_tradeoff',
        'adp_heldout_performance_': 'fig04_heldout_performance',
        'adp_ablation_safety_': 'fig05_ablation_safety',
        'adp_representative_trajectory_': 'fig06_representative_trajectory',
    }
    for prefix, folder in families.items():
        if stem.startswith(prefix):
            result = FIGURES/folder
            result.mkdir(parents=True, exist_ok=True)
            return result
    if stem == 'adp_rollout_architecture':
        result = ROOT/'output/legacy_regenerated_figures'
        result.mkdir(parents=True, exist_ok=True)
        return result
    raise ValueError(f'No manuscript destination for {stem!r}')
