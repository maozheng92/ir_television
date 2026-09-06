"""Diagnostics for IR Television (no secrets stored; still redact entity-ish fields)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .actions import (
    build_source_list,
    compute_supported_features,
    describe_homekit_entries,
    homekit_accessory_entries_for_entity,
    pick_homekit_bridge_entry_id,
    resolve_manufacturer,
)
from .const import CONF_COMMANDS, CONF_POWER_SENSOR, CONF_SOURCES, DOMAIN, HOMEKIT_DOMAIN

TO_REDACT = {"unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    commands = entry.data.get(CONF_COMMANDS) or {}
    sources = entry.data.get(CONF_SOURCES) or []
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id) or {}
    tv_id = runtime.get("tv_entity_id") if isinstance(runtime, dict) else None
    state = hass.states.get(str(tv_id)) if tv_id else None
    homekit_triples = [
        (dict(hk.data), dict(hk.options), hk.entry_id)
        for hk in hass.config_entries.async_entries(HOMEKIT_DOMAIN)
    ]
    homekit_pairs = [(data, options) for data, options, _ in homekit_triples]
    attrs = dict(state.attributes) if state is not None else {}
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
        "homekit_manufacturer": resolve_manufacturer(dict(entry.data)),
        "source_names": [
            src.get("name") for src in sources if isinstance(src, dict)
        ],
        "effective_source_list": build_source_list(sources),
        "tv_entity_id": tv_id,
        "tv_state": None
        if state is None
        else {
            "entity_id": state.entity_id,
            "state": state.state,
            "device_class": attrs.get("device_class"),
            "source": attrs.get("source"),
            "source_list": attrs.get("source_list"),
            "supported_features": attrs.get("supported_features"),
            "volume_level": attrs.get("volume_level"),
            "is_volume_muted": attrs.get("is_volume_muted"),
            "assumed_state": attrs.get("assumed_state"),
        },
        "homekit_entries": describe_homekit_entries(homekit_pairs),
        "homekit_bridge_entry_id": pick_homekit_bridge_entry_id(homekit_triples),
        "homekit_accessory_entry_ids": homekit_accessory_entries_for_entity(
            homekit_triples, str(tv_id)
        )
        if tv_id
        else [],
    }
