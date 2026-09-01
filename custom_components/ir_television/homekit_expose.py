"""Ask HomeKit to pair this TV as a standalone accessory (like Sony Bravia).

Apple will not list a Television in Control Center Remote unless it is a
HomeKit *accessory* (one entity, mode=accessory). The official HomeKit
integration only auto-creates those entries when a bridge is first set up
and ``media_player`` is in include_domains. A TV added later — this
integration — is skipped by the bridge (``exclude_accessory_mode``) and never
gets a pairing QR. Sony works because it already had that accessory entry.

This module starts the same ``source=accessory`` config flow HomeKit uses
internally. It must not be imported from ``actions.py`` (tests load that
module without Home Assistant).
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .actions import (
    collect_homekit_ports,
    homekit_accessory_entity_ids,
    next_homekit_port,
)
from .const import HOMEKIT_DOMAIN, HOMEKIT_PORT

_LOGGER = logging.getLogger(__name__)

_NOTIFY_ID_PREFIX = "ir_television_homekit_"


async def async_ensure_homekit_tv_accessory(hass: HomeAssistant, entity_id: str) -> None:
    """Create a HomeKit accessory-mode entry for this media_player if missing."""
    if hass.states.get(entity_id) is None:
        _LOGGER.debug("HomeKit expose skipped; %s has no state yet", entity_id)
        return

    entries = hass.config_entries.async_entries(HOMEKIT_DOMAIN)
    pairs = [(dict(entry.data), dict(entry.options)) for entry in entries]
    if entity_id in homekit_accessory_entity_ids(pairs):
        _LOGGER.debug("HomeKit accessory already exists for %s", entity_id)
        await _async_notify_reset_for_widget(hass, entity_id)
        return

    port = next_homekit_port(collect_homekit_ports(pairs))
    try:
        await hass.config_entries.flow.async_init(
            HOMEKIT_DOMAIN,
            context={"source": "accessory"},
            data={"entity_id": entity_id, HOMEKIT_PORT: port},
        )
    except Exception:  # noqa: BLE001 — HomeKit may be disabled or too old
        _LOGGER.exception("Could not start HomeKit accessory flow for %s", entity_id)
        await _async_notify_manual_pairing(hass, entity_id)
        return

    _LOGGER.info(
        "Started HomeKit accessory-mode pairing for %s on port %s. "
        "Scan that HomeKit entry's QR code in the Apple Home app "
        "(not the main bridge).",
        entity_id,
        port,
    )


async def _async_notify_manual_pairing(hass: HomeAssistant, entity_id: str) -> None:
    """Tell the user how to pair like Sony when auto-create fails."""
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "红外电视：需要 HomeKit 配件模式",
            "message": (
                f"无法自动为 `{entity_id}` 创建 HomeKit 配件，所以 iOS "
                "控制中心遥控器不会出现（索尼 Bravia 能出现，是因为它已经有独立配件条目）。\n\n"
                "请：设置 → 设备与服务 → 添加集成 → **HomeKit 桥接** → 配对前把模式改成 "
                f"**配件 (accessory)**，只选择 `{entity_id}`，然后在 iPhone **家庭** App "
                "中扫描这个配件的二维码（不要扫主桥）。"
            ),
            "notification_id": f"{_NOTIFY_ID_PREFIX}{entity_id}",
        },
        blocking=False,
    )


async def _async_notify_reset_for_widget(hass: HomeAssistant, entity_id: str) -> None:
    """Accessory pairing is not enough if HomeKit cached an old Television snapshot."""
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "红外电视：配件已配对但仍无 iOS Remote",
            "message": (
                f"`{entity_id}` 已经是 HomeKit **配件**。实体属性（`device_class: tv`、"
                "`source_list`、`supported_features: 23997`）足够生成 TelevisionMediaPlayer；"
                "控制中心遥控器仍不出现，通常是 HomeKit **第一次配对时缓存了旧的开关/功能位**。"
                "后来改成完整电视后，iOS 不会自动升级。\n\n"
                "请按官方 HomeKit 文档做一次 **重置配件**（索尼第一次就是按电视配对的，所以不用这步）：\n"
                "1. 开发者工具 → 动作 → `homekit.reset_accessory`，`entity_id` 填 "
                f"`{entity_id}`（或点设备上的「重置 HomeKit 配件」按钮）\n"
                "2. iPhone **家庭** App 删除 TCL\n"
                "3. 再扫这条配件的新二维码\n"
                "4. 控制中心 → 隔空播放遥控器 → **点顶部设备名**，从列表里选 TCL"
                "（默认往往还停在索尼/Apple TV 上）"
            ),
            "notification_id": f"{_NOTIFY_ID_PREFIX}reset_{entity_id}",
        },
        blocking=False,
    )
