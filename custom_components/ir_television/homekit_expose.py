"""HomeKit helper — keep pairing, align this TV with the working Bravia accessory.

Control Center Remote *does* list the official braviatv HomeKit Television
(shown as **SONY**). This IR TV is already a Home Television; iOS omits it
from that picker. The remaining deltas we can still change are:

* HAP Manufacturer (braviatv = ``Sony``; the widget label is that field)
* Living on the **same HomeKit Bridge** the hub already talks to

Do not rotate pairing identity. Do not import this module from ``actions.py``.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .actions import (
    build_bridge_filter_including,
    homekit_accessory_entries_for_entity,
    homekit_filter_dict,
    merge_homekit_entity_config,
    pick_homekit_bridge_entry_id,
    resolve_manufacturer,
)
from .const import (
    DEFAULT_HOMEKIT_MANUFACTURER,
    DOMAIN,
    HOMEKIT_DOMAIN,
    HOMEKIT_FILTER,
    HOMEKIT_INCLUDE_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)

_NOTIFY_ID = "ir_television_homekit_recreate"


def _homekit_triples(hass: HomeAssistant) -> list[tuple[dict, dict, str]]:
    triples: list[tuple[dict, dict, str]] = []
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        triples.append((dict(entry.data), dict(entry.options), entry.entry_id))
    return triples


def _manufacturer_for_tv(hass: HomeAssistant, tv_id: str) -> str:
    for entry_id, runtime in (hass.data.get(DOMAIN) or {}).items():
        if not isinstance(runtime, dict) or runtime.get("tv_entity_id") != tv_id:
            continue
        entry = hass.config_entries.async_get_entry(str(entry_id))
        if entry is not None:
            return resolve_manufacturer(dict(entry.data))
    return DEFAULT_HOMEKIT_MANUFACTURER


async def async_recreate_homekit_tv_accessory(
    hass: HomeAssistant, entity_ids: list[str]
) -> None:
    """Add this TV to Sony's bridge and refresh Accessory Information."""
    tv_id = next((eid for eid in entity_ids if eid.startswith("media_player.")), None)
    if tv_id is None or hass.states.get(tv_id) is None:
        await _async_notify(
            hass,
            "红外电视：没有 media_player 实体。",
        )
        return

    triples = _homekit_triples(hass)
    bridge_id = pick_homekit_bridge_entry_id(triples)
    manufacturer = _manufacturer_for_tv(hass, tv_id)
    bridge_note = await _async_include_on_bridge(
        hass, tv_id, bridge_id, manufacturer=manufacturer
    )
    acc_ids = homekit_accessory_entries_for_entity(triples, tv_id)

    ports: list[str] = []
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        if entry.entry_id not in acc_ids:
            continue
        blob = {**dict(entry.data), **dict(entry.options)}
        port = blob.get("port")
        ports.append(f"`{entry.title}` 端口 {port}")

    reset_note = await _async_reset_accessory(hass, tv_id)
    port_note = "、".join(ports) if ports else "未找到这条电视自己的配件模式条目（桥接拆出的配件也没问题）"
    await _async_notify(
        hass,
        (
            "控制中心列表里的 **SONY** 就是 HA 官方 braviatv 的 HomeKit 电视。"
            "HA Television **可以**进这个列表；红外电视被单独滤掉了。\n\n"
            f"{bridge_note}\n"
            f"配件条目：{port_note}。\n"
            f"{reset_note}\n\n"
            f"已把 HomeKit 制造商写成 **{manufacturer}**"
            "（和 braviatv 一样；遥控器上那台显示成 SONY）。"
            "**没有**删除配对、也没有换新二维码。\n\n"
            "请等一两分钟让 Apple TV 家庭中枢同步，再打开控制中心遥控器，"
            "**点顶部设备名**。列表里可能出现第二台 SONY，或仍显示 TCL。\n"
            "不要再删家庭 App 配件、不要再扫新码。"
        ),
    )


async def _async_include_on_bridge(
    hass: HomeAssistant,
    tv_id: str,
    bridge_id: str | None,
    *,
    manufacturer: str,
) -> str:
    """Add the TV to Sony's HomeKit Bridge and set entity_config manufacturer."""
    if not bridge_id:
        return "没有找到现有 HomeKit 桥接。请先添加与索尼同一座桥。"

    entry = hass.config_entries.async_get_entry(bridge_id)
    if entry is None:
        return "找不到 HomeKit 桥接配置条目。"

    options = dict(entry.options)
    filt = homekit_filter_dict(dict(entry.data), options)
    already = tv_id in [str(item) for item in (filt.get(HOMEKIT_INCLUDE_ENTITIES) or [])]
    options[HOMEKIT_FILTER] = build_bridge_filter_including(filt, tv_id)
    options = merge_homekit_entity_config(
        options, tv_id, manufacturer=manufacturer
    )
    hass.config_entries.async_update_entry(entry, options=options)
    try:
        await hass.config_entries.async_reload(entry.entry_id)
    except Exception:  # noqa: BLE001 — never fail the helper on HomeKit reload
        _LOGGER.exception("Failed to reload HomeKit bridge %s", entry.entry_id)
    title = entry.title or bridge_id
    if already:
        return f"`{tv_id}` 已在桥 **{title}** 的包含列表里，并写入了制造商。"
    return f"已把 `{tv_id}` 加进桥 **{title}** 的包含列表（索尼同一座桥）。"


async def _async_reset_accessory(hass: HomeAssistant, tv_id: str) -> str:
    """Refresh HAP Accessory Information without rotating the pairing identity."""
    if not hass.services.has_service(HOMEKIT_DOMAIN, "reset_accessory"):
        return "当前 HA 没有 `homekit.reset_accessory` 服务。"
    try:
        await hass.services.async_call(
            HOMEKIT_DOMAIN,
            "reset_accessory",
            {"entity_id": tv_id},
            blocking=False,
        )
    except Exception:  # noqa: BLE001
        _LOGGER.exception("homekit.reset_accessory failed for %s", tv_id)
        return f"`homekit.reset_accessory` 调用失败（`{tv_id}`）。"
    return f"已对 `{tv_id}` 调用 `homekit.reset_accessory`（只刷新配件信息）。"


async def _async_notify(hass: HomeAssistant, message: str) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "红外电视：对齐索尼 HomeKit 桥",
            "message": message,
            "notification_id": _NOTIFY_ID,
        },
        blocking=False,
    )
