"""Validate optional Basilisk backend availability."""

from __future__ import annotations

from orbinspect_dynamics.basilisk_adapter import basilisk_available


def main() -> None:
    """Print whether Basilisk is available without failing HCW workflows."""
    if basilisk_available():
        print('Basilisk available: optional backend can be configured.')
    else:
        print('Basilisk unavailable: HCW backend remains the default.')


if __name__ == '__main__':
    main()
