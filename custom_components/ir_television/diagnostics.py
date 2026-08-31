"""Diagnostics for IR Television (no secrets stored; still redact entity-ish fields)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .actions import build_source_list, compute_supported_features
from .const import CONF_COMMANDS, CONF_POWER_SENSOR, CONF_SOURCES

TO_REDACT = {"unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    commands = entry.data.get(CONF_COMMANDS) or {}
    sources = entry.data.get(CONF_SOURCES) or []
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "entry_id": entry.entry_id,
                "data": dict(entry.data),
            },
            TO_REDACT,
        ),
        "supported_features": compute_supported_features(commands, sources),
        "command_keys": sorted(commands.keys()),
        "power_sensor": entry.data.get(CONF_POWER_SENSOR),
        "source_names": [
            src.get("name") for src in sources if isinstance(src, dict)
        ],
        "effective_source_list": build_source_list(sources),
    }
