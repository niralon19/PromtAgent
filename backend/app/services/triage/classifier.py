from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import structlog
import yaml

log = structlog.get_logger(__name__)

Category = Literal["physical", "data_integrity", "coupling", "manual_review"]

_RULES_PATH = Path(__file__).parent.parent.parent.parent / "config" / "classification_rules.yaml"


class ClassificationService:
    """Rule-based alert classifier loaded from a YAML config file."""

    def __init__(self, rules_path: Path | None = None) -> None:
        self._rules: dict = {}
        self._path = rules_path or _RULES_PATH
        self._load()

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                self._rules = yaml.safe_load(f) or {}
            log.debug("classification_rules_loaded", path=str(self._path))
        except FileNotFoundError:
            log.warning("classification_rules_not_found", path=str(self._path))
            self._rules = {}

    def classify(
        self,
        alertname: str,
        labels: dict[str, str],
        annotations: dict[str, str] | None = None,
    ) -> tuple[Category, str]:
        """Classify an alert into a category.

        Returns:
            (category, reason) tuple. Falls back to "manual_review" with explanation.
        """
        annotations = annotations or {}

        # Hard label override takes priority
        label_category = labels.get("category", "").lower()
        if label_category in ("physical", "data_integrity", "coupling"):
            return label_category, f"explicit label category={label_category}"  # type: ignore[return-value]

        for category, rules in self._rules.items():
            for rule in rules:
                # Check label_hints first (exact match)
                label_hints: dict = rule.get("label_hints", {})
                label_match = all(
                    labels.get(k, "").lower() == v.lower() for k, v in label_hints.items()
                )
                if label_hints and not label_match:
                    continue

                # Check alertname patterns
                for pattern in rule.get("alertname_patterns", []):
                    if re.match(pattern, alertname, re.IGNORECASE):
                        reason = f"alertname '{alertname}' matched pattern '{pattern}' => {category}"
                        log.info("classification_decision", alertname=alertname, category=category, reason=reason)
                        return category, reason  # type: ignore[return-value]

                # Check metric_hints against annotations/labels
                text = " ".join(list(labels.values()) + list(annotations.values()) + [alertname]).lower()
                for hint in rule.get("metric_hints", []):
                    if hint.lower() in text:
                        reason = f"metric hint '{hint}' found in alert text => {category}"
                        log.info("classification_decision", alertname=alertname, category=category, reason=reason)
                        return category, reason  # type: ignore[return-value]

        reason = f"no rule matched alertname='{alertname}' — flagged for manual review"
        log.warning("classification_manual_review", alertname=alertname, labels=labels)
        return "manual_review", reason

    def reload(self) -> None:
        """Hot-reload rules without restart."""
        self._load()
