"""
Optional CBF-QP safety filter placeholder.

The Phase 8 demo uses the projection filter as the active safety layer.
"""

from __future__ import annotations


class CbfSafetyFilter:
    """Placeholder for a future control-barrier-function QP filter."""

    available = False

    def filter_command(self, *args, **kwargs):
        """Raise until a QP backend is intentionally introduced."""
        raise NotImplementedError('CBF-QP filtering is deferred to a later phase')
