"""Shared entity base — same shape as official ``braviatv.entity.BraviaTVEntity``.

HomeKit reads DeviceInfo for Accessory Information (manufacturer / model).
braviatv sets manufacturer only and leaves ``model`` empty so HomeKit falls
back to ``media_player``.title() == ``Media Player``. We do the same: do not
set ``model`` or ``name`` here (device name comes from the config entry title).
Manufacturer is user-configurable (生产企业).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .actions import resolve_manufacturer
from .const import DOMAIN


class IRTelevisionEntity:
    """Base for media_player, remote, and buttons on one TV device."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        # Match BraviaTVEntity: identifiers + manufacturer only.
        # No model (HomeKit Model → "Media Player"), no name (entry title).
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            manufacturer=resolve_manufacturer(dict(self._entry.data)),
        )
