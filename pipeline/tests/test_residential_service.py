from __future__ import annotations

import pytest

from pipeline.src.residential_service import verify_secret


def test_residential_service_refuses_to_run_unauthenticated() -> None:
    with pytest.raises(RuntimeError, match="secret is not configured"):
        verify_secret("", None)


def test_residential_service_refuses_weak_shared_secret() -> None:
    with pytest.raises(RuntimeError, match="at least 24"):
        verify_secret("too-short", "too-short")


def test_residential_service_rejects_wrong_secret() -> None:
    with pytest.raises(PermissionError, match="unauthorized"):
        verify_secret("expected-secret-is-long-enough", "wrong")


def test_residential_service_accepts_matching_secret() -> None:
    verify_secret("expected-secret-is-long-enough", "expected-secret-is-long-enough")
