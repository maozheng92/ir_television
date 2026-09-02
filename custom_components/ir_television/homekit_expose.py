"""Recreate the HomeKit *media_player* accessory with a new pairing identity.

A complete Television IID dump (D8 + E8 RemoteKey + HDMI inputs + speaker) means
HomeKit already built the right accessory. ``homekit.reset_accessory`` only
rebuilds services on the *same* pairing MAC — iOS devices that once failed
``pair verify`` keep a stale UUID and never list the TV in Control Center.

Deleting the HomeKit config entry and starting a fresh ``source=accessory``
flow is what actually rotates the identity. Sony Bravia does not need this
because its accessory was paired cleanly the first time.

Do not import this module from ``actions.py``.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .actions import (
    collect_homekit_ports,
    homekit_entries_for_entity,
    next_homekit_port,
)
from .const import HOMEKIT_DOMAIN, HOMEKIT_PORT

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
    """Remove existing HomeKit entries for these entities and pair the TV again."""
    tv_id = next((eid for eid in entity_ids if eid.startswith("media_player.")), None)
    if tv_id is None or hass.states.get(tv_id) is None:
        _LOGGER.warning("Cannot recreate HomeKit TV accessory; media_player is missing")
        await _async_notify(
            hass,
            "红外电视：没有 media_player 实体，无法重建 HomeKit 配件。",
        )
        return

    triples = _homekit_triples(hass)
    to_remove: list[str] = []
    for eid in entity_ids:
        for entry_id in homekit_entries_for_entity(triples, eid):
            if entry_id not in to_remove:
                to_remove.append(entry_id)

    for entry_id in to_remove:
        try:
            await hass.config_entries.async_remove(entry_id)
            _LOGGER.info("Removed HomeKit entry %s before recreating TV accessory", entry_id)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not remove HomeKit entry %s", entry_id)

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
                f"无法自动为 `{tv_id}` 创建 HomeKit 配件。请：设置 → 设备与服务 → 添加集成 → "
                "**HomeKit 桥接** → 模式选 **配件 (accessory)**，只勾选 `{tv_id}`。"
            ),
        )
        return

    removed_note = (
        f"已删除 {len(to_remove)} 条旧 HomeKit 条目。" if to_remove else "原来没有对应的 HomeKit 条目。"
    )
    await _async_notify(
        hass,
        (
            f"{removed_note} 已为 `{tv_id}` 新建 **配件模式** HomeKit（端口 {port}）。\n\n"
            "你贴出的 iids 本来就是完整 Television（RemoteKey + HDMI1–4 + 扬声器）。"
            "控制中心仍不列出，是 **配对身份没换掉**（`reset_accessory` 不够），"
            "或和家里 **原厂 TCL HomeKit/AirPlay** 同名抢发现。"
            "索尼出现在「隔空播放遥控器」里，经常是电视自己的 AirPlay 2，不是 HA braviatv。\n\n"
            "请立刻：\n"
            "1. iPhone **家庭** App 删除所有叫 TCL / 红外电视 / TCL 遥控器 的配件（每台苹果设备都删）\n"
            "2. HA **设置 → 设备与服务** 打开刚出现的那条 HomeKit，扫 **新二维码**（不要扫主桥）\n"
            "3. 若家里已有原厂 TCL：把本集成设备改名为 **TCL红外** 再点一次本按钮\n"
            "4. 用 Discovery 看 `_hap._tcp`：`ci` 必须是 31，配对成功后 `sf` 必须是 **0**"
            "（`sf=1` 表示还没进家庭 App）。\n"
            "5. `sf=0` 之后：家庭 App 里应是电视图标；控制中心遥控器 **点顶部设备名** 选这台"
            "（默认常停在索尼/原厂 TCL 上）。`md=TCL` 和原厂重名时请改名为 TCL红外 再点一次本按钮"
        ),
    )


async def _async_notify(hass: HomeAssistant, message: str) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "红外电视：重建 HomeKit 电视配件",
            "message": message,
            "notification_id": _NOTIFY_ID,
        },
        blocking=False,
    )
