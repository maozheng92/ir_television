# IR Television / 红外电视

Home Assistant 自定义集成：把普通红外电视变成 **Television Media Player**（`device_class=tv`），供 **iOS 控制中心的「隔空播放遥控器 / Apple TV Remote」**（Apple HomeKit）使用。这不是 Home Assistant Companion 的主屏幕小组件。

每条按键或输入源可以走 **红外遥控器**（`remote.send_command`：官方 Broadlink 或 Logitech Harmony Hub）或任意 **按钮实体**（`button.press`）。图形化 Config Flow / Options Flow，无需 YAML。红外设备列表按所选遥控器切换：Harmony Hub 对应 `harmony_UNIQUE_ID.conf`，Broadlink 对应 `broadlink_remote_MACADDRESS_codes`。

A Home Assistant custom integration that exposes a dumb IR television as a **Television Media Player** (`device_class=tv`) so the **Apple Control Center Remote** (HomeKit `TelevisionMediaPlayer`) can control it. This is **not** the Home Assistant Companion home-screen widget.

Each key or input source is either an **IR remote** (`remote.send_command`: Broadlink or Logitech Harmony Hub) or a **button entity** (`button.press`). Setup is a graphical wizard — no YAML required. Device lists follow the selected remote: Harmony Hub → `harmony_UNIQUE_ID.conf`, Broadlink → `broadlink_remote_MACADDRESS_codes`.
