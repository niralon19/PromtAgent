from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


# Label keys that identify the "what" of an alert (not the noisy "value")
_FINGERPRINT_LABEL_KEYS = (
    "alertname",
    "hostname",
    "host",
    "instance",
    "service",
    "datacenter",
    "rack",
    "category",
    "job",
    "severity",
)

_WINDOW_MINUTES = 5


def _time_bucket(dt: datetime) -> int:
    """Collapse timestamp to 5-minute windows so bursts get the same fingerprint."""
    epoch_seconds = int(dt.timestamp())
    return epoch_seconds // (_WINDOW_MINUTES * 60)


def compute_fingerprint(labels: dict[str, str], received_at: datetime | None = None) -> str:
    """Compute a stable fingerprint for an alert.

    Two alerts with the same significant labels arriving within the same
    5-minute window produce the same fingerprint, enabling deduplication.

    Args:
        labels: Alert label dict (from Grafana payload).
        received_at: When the alert arrived (defaults to now).

    Returns:
        16-character hex string (SHA-256 prefix).
    """
    if received_at is None:
        received_at = datetime.now(timezone.utc)

    significant = {k: labels[k] for k in _FINGERPRINT_LABEL_KEYS if k in labels}
    significant["_window"] = str(_time_bucket(received_at))

    key = json.dumps(significant, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]
