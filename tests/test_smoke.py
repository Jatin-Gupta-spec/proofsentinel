"""Smoke test: the package is installed and importable."""

import proofsentinel


def test_package_imports() -> None:
    assert proofsentinel.__doc__ is not None