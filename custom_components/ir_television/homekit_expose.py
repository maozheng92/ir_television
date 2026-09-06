"""HomeKit helper — do not rotate pairing identity.

Control Center Remote enumerates TVs the **home hub** (Apple TV) can HAP-talk
to. Deleting the accessory-mode entry and issuing a new QR breaks hub pairing
(``pair verify without being paired first``) while the iPhone Home app still
shows a TV tile. That matches: Home = TV icon, Remote list = SONY + Apple TVs.

Do not import this module from ``actions.py``.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .actions import (
    build_bridge_filter_including,
    homekit_accessory_entries_for_entity,
    homekit_filter_dict,
    pick_homekit_bridge_entry_id,
)
from .const import HOMEKIT_DOMAIN, HOMEKIT_FILTER, HOMEKIT_INCLUDE_ENTITIES

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
    """Keep the existing accessory pairing; explain why Remote may omit this TV."""
    tv_id = next((eid for eid in entity_ids if eid.startswith("media_player.")), None)
    if tv_id is None or hass.states.get(tv_id) is None:
        await _async_notify(
            hass,
            "红外电视：没有 media_player 实体。",
        )
        return

    triples = _homekit_triples(hass)
    bridge_id = pick_homekit_bridge_entry_id(triples)
    bridge_note = await _async_include_on_bridge(hass, tv_id, bridge_id)
    acc_ids = homekit_accessory_entries_for_entity(triples, tv_id)

    ports: list[str] = []
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        if entry.entry_id not in acc_ids:
            continue
        blob = {**dict(entry.data), **dict(entry.options)}
        port = blob.get("port")
        title = entry.title
        ports.append(f"`{title}` 端口 {port}")

    port_note = "、".join(ports) if ports else "没有找到这条电视的配件模式 HomeKit 条目"
    await _async_notify(
        hass,
        (
            f"{bridge_note}\n"
            f"配件条目：{port_note}。**没有**删除或换新二维码"
            "（换身份会让 Apple TV 中枢 pair verify 失败，家庭 App 仍显示电视，"
            "遥控器列表却只有索尼和 Apple TV）。\n\n"
            "家庭 App 已是电视图标、遥控器切换列表只有 SONY + Apple TV 时：\n"
            "1. 对比遥控器里的 **SONY** 和家庭 App 里索尼配件的**全名**"
            "（例如 BRAVIA KD-55X9000B）。全名不同，说明 Widget 里的 SONY"
            "可能不是 HA braviatv 那条配件。\n"
            "2. 控制中心遥控器的 HomeKit 电视由 **Apple TV 家庭中枢**收录，"
            "不是 iPhone 家庭 App。中枢必须能连上上面的 **配件端口**"
            "（和索尼配件不是同一个端口）。看 HA 日志是否还有 "
            "`pair verify without being paired first`。\n"
            "3. **不要再点重建/重配。** 家庭 App 里删掉红外电视后，等两台"
            "Apple TV 都同步（家庭设置 → 家庭中枢为已连接），再用**同一条**"
            "已有配件的二维码加回一次，等几分钟让中枢学会这台电视。\n"
            "4. 决定性试验：暂时关掉/删除家庭里 **HA 的索尼电视配件**"
            "（不是拆电视电源）。若此时 Widget 仍没有红外电视，"
            "则 Widget 里的 SONY 本来就不是 HA HomeKit 电视。"
        ),
    )


async def _async_include_on_bridge(
    hass: HomeAssistant, tv_id: str, bridge_id: str | None
) -> str:
    """Add the TV to an existing HomeKit Bridge filter (Sony's include list)."""
    if not bridge_id:
        return "没有找到现有 HomeKit 桥接。"

    entry = hass.config_entries.async_get_entry(bridge_id)
    if entry is None:
        return "找不到 HomeKit 桥接配置条目。"

    options = dict(entry.options)
    filt = homekit_filter_dict(dict(entry.data), options)
    already = tv_id in [str(item) for item in (filt.get(HOMEKIT_INCLUDE_ENTITIES) or [])]
    options[HOMEKIT_FILTER] = build_bridge_filter_including(filt, tv_id)
    hass.config_entries.async_update_entry(entry, options=options)
    title = entry.title or bridge_id
    if already:
        return f"`{tv_id}` 已在桥 **{title}** 的包含列表里。"
    return f"已把 `{tv_id}` 留在桥 **{title}** 的包含列表里。"


async def _async_notify(hass: HomeAssistant, message: str) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "红外电视：遥控器列表与家庭中枢",
            "message": message,
            "notification_id": _NOTIFY_ID,
        },
        blocking=False,
    )
