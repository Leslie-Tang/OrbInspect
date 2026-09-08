"""Reader-facing names, kept separate from immutable experiment identifiers."""

PROFILE_LABELS = {'required06': '6-target', 'required09': '9-target', 'required12': '12-target'}
OBJECTIVE_LABELS = {'coverage_only80': r'Coverage-only (80\%)'}

REPRESENTATIVE_CASE_LEAD = (
    'The representative test case is the jointly completed scenario nearest the '
    'median ADP-minus-local graph-cost difference. '
    'Ties are resolved deterministically using the scenario identifier. '
)


def profile_label(identifier: str) -> str:
    """Require an explicit publication label rather than print a raw code key."""
    return PROFILE_LABELS[identifier]


def objective_label(identifier: str) -> str:
    """Render the diagnostic objective with its threshold and academic wording."""
    return OBJECTIVE_LABELS[identifier]
