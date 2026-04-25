from __future__ import annotations

from typing import Any

import structlog

from app.tools.base import Tool

log = structlog.get_logger(__name__)


class ToolRegistry:
    """Central registry for all diagnostic tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool_class: type[Tool]) -> type[Tool]:
        """Register a Tool class. Returns the class (for use as decorator)."""
        instance = tool_class()
        name = tool_class.name
        if name in self._tools:
            log.warning("tool_already_registered", tool=name)
        self._tools[name] = instance
        log.debug("tool_registered", tool=name, categories=tool_class.categories)
        return tool_class

    def get(self, name: str) -> Tool:
        """Retrieve tool by name. Raises KeyError if not found."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool '{name}' is not registered") from exc

    def list_for_category(self, category: str) -> list[Tool]:
        """Return all tools applicable to a given incident category."""
        return [t for t in self._tools.values() if category in t.categories]

    def list_all(self) -> list[Tool]:
        return list(self._tools.values())

    def list_all_schemas_for_llm(self) -> list[dict[str, Any]]:
        """Return Anthropic-compatible tool schemas for all registered tools."""
        return [t.anthropic_schema() for t in self._tools.values()]

    def schemas_for_category(self, category: str) -> list[dict[str, Any]]:
        return [t.anthropic_schema() for t in self.list_for_category(category)]


# Singleton instance used everywhere
tool_registry = ToolRegistry()


def register_tool(tool_class: type[Tool]) -> type[Tool]:
    """Class decorator that registers a Tool with the global registry."""
    tool_registry.register(tool_class)
    return tool_class
