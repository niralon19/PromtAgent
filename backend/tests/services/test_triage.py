from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.triage.fingerprint import compute_fingerprint
from app.services.triage.classifier import ClassificationService


# ---------------------------------------------------------------------------
# Fingerprint tests
# ---------------------------------------------------------------------------


def test_fingerprint_stable_same_labels_same_window() -> None:
    labels = {"alertname": "HighCPU", "hostname": "server-01", "severity": "critical"}
    now = datetime.now(timezone.utc)
    fp1 = compute_fingerprint(labels, received_at=now)
    fp2 = compute_fingerprint(labels, received_at=now)
    assert fp1 == fp2


def test_fingerprint_different_hostname() -> None:
    base = {"alertname": "HighCPU", "hostname": "server-01"}
    other = {"alertname": "HighCPU", "hostname": "server-02"}
    now = datetime.now(timezone.utc)
    assert compute_fingerprint(base, now) != compute_fingerprint(other, now)


def test_fingerprint_is_16_chars() -> None:
    fp = compute_fingerprint({"alertname": "Test", "hostname": "h1"})
    assert len(fp) == 16


def test_fingerprint_ignores_irrelevant_labels() -> None:
    labels_a = {"alertname": "HighCPU", "hostname": "s1", "extra_noise": "abc"}
    labels_b = {"alertname": "HighCPU", "hostname": "s1", "extra_noise": "xyz"}
    now = datetime.now(timezone.utc)
    # extra_noise is NOT in _FINGERPRINT_LABEL_KEYS, so fingerprints should match
    assert compute_fingerprint(labels_a, now) == compute_fingerprint(labels_b, now)


# ---------------------------------------------------------------------------
# Classifier tests
# ---------------------------------------------------------------------------


def test_classifier_physical_by_alertname() -> None:
    clf = ClassificationService()
    cat, reason = clf.classify("HighCPUUsage", {"hostname": "s1"})
    assert cat == "physical"


def test_classifier_data_integrity_by_alertname() -> None:
    clf = ClassificationService()
    cat, reason = clf.classify("DataFreshnessAlert", {"hostname": "s1"})
    assert cat == "data_integrity"


def test_classifier_coupling_by_alertname() -> None:
    clf = ClassificationService()
    cat, reason = clf.classify("BGPPeerDown", {"hostname": "router-1"})
    assert cat == "coupling"


def test_classifier_label_override() -> None:
    clf = ClassificationService()
    cat, reason = clf.classify("SomeUnknownAlert", {"hostname": "s1", "category": "coupling"})
    assert cat == "coupling"
    assert "explicit label" in reason


def test_classifier_unknown_falls_to_manual_review() -> None:
    clf = ClassificationService()
    cat, reason = clf.classify("XyzUnmatchableAlert999", {"hostname": "s1"})
    assert cat == "manual_review"


def test_classifier_memory_alert() -> None:
    clf = ClassificationService()
    cat, _ = clf.classify("MemoryUsageHigh", {})
    assert cat == "physical"


def test_classifier_link_down() -> None:
    clf = ClassificationService()
    cat, _ = clf.classify("LinkDownAlert", {})
    assert cat == "coupling"


# ---------------------------------------------------------------------------
# DedupService tests
# ---------------------------------------------------------------------------


async def test_dedup_no_existing_returns_none() -> None:
    from app.services.triage.dedup import DedupService
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    svc = DedupService(redis_client=None)
    result = await svc.check_duplicate("abc123", mock_db)
    assert result is None


async def test_dedup_finds_existing_incident() -> None:
    from app.services.triage.dedup import DedupService
    from app.db.models import Incident

    mock_incident = MagicMock(spec=Incident)
    mock_incident.id = uuid.uuid4()
    mock_incident.status = "triaging"
    mock_incident.recurrence_count = 0

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_incident

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    svc = DedupService(redis_client=None)
    result = await svc.check_duplicate("fp123", mock_db)
    assert result is mock_incident
