"""Shared entity base — same shape as official ``braviatv.entity.BraviaTVEntity``.

HomeKit reads DeviceInfo for Accessory Information (manufacturer / model).
``model`` is ``Media Player`` so the Devices list subtitle matches a typical
TCL / HomeKit television (not a second copy of the manufacturer).
Manufacturer is user-configurable (生产企业). Device name comes from the
config entry title.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .actions import resolve_manufacturer
from .const import DEVICE_MODEL, DOMAIN


class IRTelevisionEntity:
    """Base for media_player, remote, and buttons on one TV device."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            manufacturer=resolve_manufacturer(dict(self._entry.data)),
            model=DEVICE_MODEL,
        )
