"""Put the IR TV on the same HomeKit path as official Sony Bravia.

Sony TVs in this setup have **no AirPlay and no native HomeKit**. The working
path is:

1. Official ``braviatv`` ``media_player`` (device_class=tv)
2. Home Assistant **HomeKit Bridge** includes that player
3. HA auto-creates a separate **accessory-mode** HomeKit entry (HAP does not
   allow Television on a bridge)
4. Pair that accessory in the Apple Home app → Control Center Remote

This module does the same for our ``media_player``: add it to the existing
HomeKit Bridge filter, then create (or recreate) the accessory-mode entry HA
would have split out. Never delete a bridge-mode entry — that would drop Sony.

Do not import this module from ``actions.py``.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .actions import (
    build_bridge_filter_including,
    collect_homekit_ports,
    homekit_accessory_entries_for_entity,
    homekit_filter_dict,
    next_homekit_port,
    pick_homekit_bridge_entry_id,
)
from .const import (
    HOMEKIT_DOMAIN,
    HOMEKIT_FILTER,
    HOMEKIT_INCLUDE_ENTITIES,
    HOMEKIT_PORT,
)

_LOGGER = logging.getLogger(__name__)

_NOTIFY_ID = "ir_television_homekit_recreate"


def _homekit_triples(hass: HomeAssistant) -> list[tuple[dict, dict, str]]:
    triples: list[tuple[dict, dict, str]] = []
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        triples.append((dict(entry.data), dict(entry.options), entry.entry_id))
    return triples


async def async_recreate_homekit_tv_accessory(
    hass: HomeAssistant, entity_ids: list[str]
) -> None:
    """Add the TV to the existing HomeKit Bridge, then pair it as an accessory."""
    tv_id = next((eid for eid in entity_ids if eid.startswith("media_player.")), None)
    if tv_id is None or hass.states.get(tv_id) is None:
        _LOGGER.warning("Cannot expose IR TV to HomeKit; media_player is missing")
        await _async_notify(
            hass,
            "红外电视：没有 media_player 实体，无法按索尼方式接入 HomeKit。",
        )
        return

    triples = _homekit_triples(hass)
    to_remove: list[str] = []
    for eid in entity_ids:
        for entry_id in homekit_accessory_entries_for_entity(triples, eid):
            if entry_id not in to_remove:
                to_remove.append(entry_id)

    for entry_id in to_remove:
        try:
            await hass.config_entries.async_remove(entry_id)
            _LOGGER.info(
                "Removed accessory-mode HomeKit entry %s before re-exposing TV",
                entry_id,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not remove HomeKit accessory entry %s", entry_id)

    triples = _homekit_triples(hass)
    bridge_id = pick_homekit_bridge_entry_id(triples)
    bridge_note = await _async_include_on_bridge(hass, tv_id, bridge_id)

    remaining = [
        (dict(entry.data), dict(entry.options))
        for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN)
    ]
    port = next_homekit_port(collect_homekit_ports(remaining))
    try:
        await hass.config_entries.flow.async_init(
            HOMEKIT_DOMAIN,
            context={"source": "accessory"},
            data={"entity_id": tv_id, HOMEKIT_PORT: port},
        )
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Could not start HomeKit accessory flow for %s", tv_id)
        await _async_notify(
            hass,
            (
                f"{bridge_note}\n\n"
                f"无法自动为 `{tv_id}` 创建配件模式 HomeKit。请：设置 → 设备与服务 → "
                "添加集成 → **HomeKit 桥接** → 勾选 `media_player` 域"
                "（和当初加索尼一样）。HA 会为每台电视自动拆出一条配件，再扫**那条配件**的二维码，"
                "不要扫主桥。"
            ),
        )
        return

    removed_note = (
        f"已删除 {len(to_remove)} 条旧的**配件模式** HomeKit（主桥未动）。"
        if to_remove
        else "原来没有这条电视的配件模式条目。"
    )
    await _async_notify(
        hass,
        (
            f"{removed_note} {bridge_note} "
            f"已为 `{tv_id}` 新建配件模式 HomeKit（端口 {port}），"
            "机制与官方 HomeKit 桥接给索尼 Bravia 自动拆配件相同。\n\n"
            "**索尼没有 AirPlay，也没有原厂 HomeKit。** "
            "能出现在「隔空播放遥控器」里，是因为："
            "官方 Sony Bravia TV 集成 → **HomeKit 桥接**（包含 `media_player`）→ "
            "HA 再为电视拆出配件模式 → 家庭 App 配对那条配件。\n\n"
            "请立刻：\n"
            "1. iPhone **家庭** App 删除旧的 TCL / 红外电视配件（每台苹果设备都删；"
            "**不要**删索尼那条）\n"
            "2. HA **设置 → 设备与服务** 打开刚出现的那条 HomeKit **配件**，扫 **新二维码**"
            "（不要扫主桥的码）\n"
            "3. 控制中心 → 隔空播放遥控器 → **点顶部设备名**，从列表里选这台"
            "（默认常停在索尼上）\n"
            "4. 用 Discovery 看 `_hap._tcp`：这条电视配件 `ci` 必须是 **31**，"
            "配对后 `sf` 必须是 **0**。主桥是 `ci=2`，遥控器不认主桥上的电视。"
        ),
    )


async def _async_include_on_bridge(
    hass: HomeAssistant, tv_id: str, bridge_id: str | None
) -> str:
    """Add the TV to an existing HomeKit Bridge filter (Sony's include list)."""
    if not bridge_id:
        return (
            "没有找到现有 **HomeKit 桥接**。"
            "请先添加一次 HomeKit 桥接（和当初加索尼一样，勾选 `media_player`），"
            "再点本按钮。"
        )

    entry = hass.config_entries.async_get_entry(bridge_id)
    if entry is None:
        return "找不到 HomeKit 桥接配置条目。"

    options = dict(entry.options)
    filt = homekit_filter_dict(dict(entry.data), options)
    already = tv_id in [str(item) for item in (filt.get(HOMEKIT_INCLUDE_ENTITIES) or [])]
    options[HOMEKIT_FILTER] = build_bridge_filter_including(filt, tv_id)
    hass.config_entries.async_update_entry(entry, options=options)
    try:
        await hass.config_entries.async_reload(entry.entry_id)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Could not reload HomeKit bridge %s", bridge_id)

    title = entry.title or bridge_id
    if already:
        return f"`{tv_id}` 本来就在 HomeKit 桥 **{title}** 的包含列表里。"
    return f"已把 `{tv_id}` 加进 HomeKit 桥 **{title}** 的包含列表（与索尼同一座桥）。"


async def _async_notify(hass: HomeAssistant, message: str) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "红外电视：按索尼方式接入 HomeKit",
            "message": message,
            "notification_id": _NOTIFY_ID,
        },
        blocking=False,
    )
