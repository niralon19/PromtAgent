from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

_ACTIONS_PATH = Path(__file__).parent.parent.parent.parent / "config" / "actions.yaml"


class ActionDefinition(BaseModel):
    action_key: str
    description: str
    target_fields: list[str]
    tier: int
    requires_approval: bool
    estimated_risk: Literal["low", "medium", "high"]


class SuggestedAction(BaseModel):
    action_key: str
    parameters: dict
    rationale: str
    estimated_risk: Literal["low", "medium", "high"]
    requires_approval: bool
    tier: int = 0


class ActionAllowlist:
    """Registry of permitted actions the agent can suggest."""

    def __init__(self, path: Path | None = None) -> None:
        self._actions: dict[str, ActionDefinition] = {}
        self._load(path or _ACTIONS_PATH)

    def _load(self, path: Path) -> None:
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            for item in raw.get("actions", []):
                defn = ActionDefinition(**item)
                self._actions[defn.action_key] = defn
        except FileNotFoundError:
            pass

    def is_valid(self, action_key: str) -> bool:
        return action_key in self._actions

    def get(self, action_key: str) -> ActionDefinition | None:
        return self._actions.get(action_key)

    def all_keys(self) -> list[str]:
        return list(self._actions.keys())


# Singleton
action_allowlist = ActionAllowlist()
