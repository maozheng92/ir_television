"""Send a configured action via IR remote or button entities."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .actions import (
    action_is_valid,
    button_press_interval,
    build_button_service_data,
    build_remote_service_data,
    expand_button_presses,
)
from .const import ACTION_BROADLINK, ACTION_BUTTON, ATTR_ENTITY_ID, ATTR_TYPE

_LOGGER = logging.getLogger(__name__)


async def async_send_action(
    hass: HomeAssistant,
    action: dict[str, Any] | None,
    context: str,
) -> bool:
    """Send one mapped command. Never raises to the caller."""
    if not action_is_valid(action):
        _LOGGER.warning("IR Television: %s has no valid command mapping", context)
        return False

    assert action is not None
    action_type = action[ATTR_TYPE]

    try:
        if action_type == ACTION_BROADLINK:
            await hass.services.async_call(
                "remote",
                "send_command",
                build_remote_service_data(action),
                blocking=True,
            )
            return True
        if action_type == ACTION_BUTTON:
            presses = expand_button_presses(action)
            interval = button_press_interval(action)
            for index, entity_id in enumerate(presses):
                await hass.services.async_call(
                    "button",
                    "press",
                    build_button_service_data(
                        {ATTR_TYPE: ACTION_BUTTON, ATTR_ENTITY_ID: entity_id}
                    ),
                    blocking=True,
                )
                if index < len(presses) - 1 and interval > 0:
                    await asyncio.sleep(interval)
            return True
    except Exception as err:  # noqa: BLE001 — IR backends fail often; never crash
        _LOGGER.warning(
            "IR Television: failed to send %s (%s): %s",
            context,
            action_type,
            err,
        )
        return False

    _LOGGER.warning("IR Television: unknown action type for %s: %s", context, action_type)
    return False
