# IR Television / 红外电视

Home Assistant 自定义集成：把普通红外电视变成 **Television Media Player**（`device_class=tv`），供 **iOS 控制中心的「隔空播放遥控器 / Apple TV Remote」**（Apple HomeKit）使用。这不是 Home Assistant Companion 的主屏幕小组件。

每条按键或输入源可以走 **Broadlink 红外**（`remote.send_command`）或任意 **按钮实体**（`button.press`）。图形化 Config Flow / Options Flow，无需 YAML。

A Home Assistant custom integration that exposes a dumb IR television as a **Television Media Player** (`device_class=tv`) so the **Apple Control Center Remote** (HomeKit `TelevisionMediaPlayer`) can control it. This is **not** the Home Assistant Companion home-screen widget.

Each key or input source is either **Broadlink IR** (`remote.send_command`) or a **button entity** (`button.press`). Setup is a graphical wizard — no YAML required.

---

## 中文

### 它是什么

- 平台：`media_player`，设备类别 `tv`（Apple HomeKit 会把它识别为 `TelevisionMediaPlayer`）
- 电源状态：默认乐观 / 假定；可选用 `binary_sensor` 作为真实开关回读（智能插座、电流钳、HDMI-CEC、模板等）
- 未配置自定义输入源时，仍会自动暴露一个默认源 **TV**，并始终带上 `SELECT_SOURCE`（HomeKit 需要 `CHAR_ACTIVE_IDENTIFIER`）
- 方向键、返回、主页、菜单、信息：配置后会出现在同一设备上的额外 `button` 实体；**同时**由本集成监听 HomeKit 事件 `homekit_tv_remote_key_pressed`，控制中心遥控器的方向键会发红外

### 为什么 iOS 控制中心遥控器会出现

这是 **系统控制中心 → 隔空播放遥控器 / Apple TV Remote**，不是 Companion 主屏幕小组件。

Apple 只会在以下条件都满足时显示该遥控器：

1. 实体看起来像真正的 HomeKit 电视：`device_class=tv`、`source_list` 至少一个输入源、`supported_features` 含 `SELECT_SOURCE`，以及已映射的开/关等功能。
2. 通过 Home Assistant 的 **HomeKit 桥接** 暴露；Apple **要求电视作为独立配件（accessory 模式）**，不能混在主桥里。必须在「家庭」App 里**单独配对**这个电视配件。
3. 在 iPhone 上启用 **控制中心 → 隔空播放遥控器 / 遥控器**。

本集成会：

| 条件 | 本集成的行为 |
| --- | --- |
| `device_class=tv` | 始终为 `MediaPlayerDeviceClass.TV` |
| 至少一个输入源 | 用户未添加源时使用默认 **TV** |
| `SELECT_SOURCE` | 始终加入 `supported_features` |
| 方向键 | 监听 `homekit_tv_remote_key_pressed` 并映射到已配置的红外/按钮 |

其它功能位仍按你映射的指令动态计算：

| 功能 | 需要映射的指令 |
| --- | --- |
| 开 / 关 | `turn_on` / `turn_off`，或单独的 `power_toggle` |
| 音量加减 | `volume_up` / `volume_down` |
| 静音 | `volume_mute` |
| 播放 / 暂停 | `play`、`pause`，或只有一个 `play_pause` |
| 停止 | `stop`（可选） |
| 下一首 / 上一首 | `next_track` / `previous_track`（频道加减或切歌） |

HomeKit 方向键映射（未映射则忽略）：

| 控制中心按键 | 指令（回退） |
| --- | --- |
| 上 / 下 / 左 / 右 | `up` / `down` / `left` / `right` |
| 选择 | `ok` |
| 返回 | `back` |
| 退出 / 主页 | `home`，没有则用 `back` |
| 信息 | `info` |
| 播放/暂停 | `play_pause`，没有则用 `play` 或 `pause` |
| 下一首 / 上一首 | `next_track` / `previous_track` |
| 快进 / 快退 | `next_track` / `previous_track`，没有则用 `right` / `left` |

### 让遥控器出现：完整步骤

**1. 安装本集成并重启**

把仓库里的 **`custom_components/ir_television/` 整个文件夹** 复制到 Home Assistant 配置目录（不要扁平化、不要只拷文件）：

```text
<config>/custom_components/ir_television/manifest.json
```

Home Assistant OS / Container 上一般是：

```text
/config/custom_components/ir_television/manifest.json
```

然后 **完整重启 Home Assistant**（仅重新加载前端不够）。

HACS：把此仓库加为 Integration 自定义仓库，下载 **红外电视 / IR Television**，再重启。

**2. 添加电视并映射按键**

设置 → 设备与服务 → 添加集成 → 搜索 **红外电视** / **IR Television**。至少映射电源；方向键请映射上/下/左/右/确定/返回，控制中心遥控器的 D-pad 才会发红外。输入源可选（不填也会有默认 **TV**）。

**3. 用 HomeKit 配件模式暴露这台电视（必须单独配对）**

Apple 不允许把电视混在主 HomeKit 桥里。

快捷做法（推荐）：

1. 设置 → 设备与服务 → 添加集成 → **HomeKit 桥接**
2. 选择包含 `media_player` 的域（或只包含这台电视）
3. 完成向导。Home Assistant 会为必须走 **配件模式** 的电视**自动再创建一个独立的 HomeKit 条目**
4. 在前端通知或该 HomeKit 条目上查看 **配对二维码 / PIN**
5. iPhone 打开 **家庭** App → 添加配件 → 扫描该电视配件的二维码（**不是**主桥的码）
6. 把它放进房间并完成设置

只添加这一台电视时：

1. 新建一个 HomeKit 桥接，**配对前**打开选项
2. 把模式改成 **accessory（配件）**
3. 只选择这台 `media_player.*` 电视实体
4. 在「家庭」App 中配对该配件

若电视以前被当成普通开关暴露过：从 HomeKit 里移除后重新添加，或对实体执行 `homekit.reset_accessory`。

**4. 打开控制中心遥控器**

1. iPhone：**设置 → 控制中心**，确保已加入 **隔空播放遥控器** / **遥控器** / Apple TV Remote
2. 从屏幕右上角下滑打开控制中心，点遥控器图标
3. 应能看到刚配对的那台电视。电源、音量走 `media_player`；方向键走本集成的 HomeKit 事件

同一局域网；电视配件必须已在「家庭」中配对。主桥里有这台电视、配件模式未配对时，遥控器**不会**出现。

### 前提条件

- Home Assistant 2024.1 或更新
- **二选一或混用：** 官方 [Broadlink](https://www.home-assistant.io/integrations/broadlink/)（已学习红外码），或已有的 `button.*` 实体
- 官方 [HomeKit 桥接](https://www.home-assistant.io/integrations/homekit/)（控制中心遥控器需要）

**请先在 Broadlink 集成里学习红外**，再添加本集成。本集成不会学习红外，只会调用 `remote.send_command`。

### 添加后仍搜不到集成时

1. 确认 `manifest.json` 就在 `custom_components/ir_television/` 下，且 `"domain": "ir_television"`
2. 完整重启一次
3. 搜索 **红外电视**、**IR Television** 或 **ir_television**
4. 设置 → 系统 → 日志，查找 `ir_television`
5. 浏览器强制刷新或无痕窗口

### 添加集成（向导）

1. **设置 → 设备与服务 → 添加集成**
2. 搜索 **IR Television** / **红外电视**
3. 按向导操作：起名 → 可选默认 Broadlink → 电源 → 可选电源传感器 → 音量/播放/频道 → 方向键（控制中心 D-pad）→ 可选输入源

之后可在集成卡片上点 **配置** 修改。保存后会自动重新加载实体。

### 如何映射 Broadlink

1. 在官方 Broadlink 集成中学习按键，记住 **设备名** 和 **指令名**
2. 本集成里控制方式选 **Broadlink 红外**
3. 选择 `remote.xxx`（或使用向导里的默认遥控器）
4. 填写设备名和指令名，例如 `power_on`、`hdmi_1`

```yaml
service: remote.send_command
data:
  entity_id: remote.xxx
  device: living_room_tv   # 可选
  command: power_on
  num_repeats: 1
```

Broadlink 实体暂时不可用时，本集成**不会崩溃**，只会在日志里写警告。

### 如何映射按钮

控制方式选 **按钮实体**，选择任意 `button.*`，运行时调用 `button.press`。同一台电视可以混用：电源走红外，某个输入源走按钮。

### 用 binary_sensor 做状态回读

红外电视默认没有电源反馈。如果你有一个能反映电视是否开机的 `binary_sensor`（电流/功率、HDMI-CEC、模板等），可在向导里指定为**电源状态传感器**：

- 传感器 `on` → 电视开机；`off` → 电视关机（可勾选反转）
- 配置后电源不再是假定状态；传感器变化会立刻更新实体
- `unavailable` / `unknown` 时保留上一次明确状态
- 清空该字段即恢复假定开关。静音和当前输入源仍是本地乐观状态

### 自定义输入源

每个源包含显示名称和动作（Broadlink 或按钮）。选择源会发送对应指令，并乐观更新当前 `source`。未添加任何源时，实体仍会报告 `source_list: ["TV"]`（无红外动作），以满足 HomeKit。

---

## English

### What it is

A HACS-ready custom component (`custom_components/ir_television`) that creates one TV device with:

- A `media_player` (`MediaPlayerDeviceClass.TV`)
- A default **TV** input source when you configured none, and **always** `SELECT_SOURCE` (HomeKit `CHAR_ACTIVE_IDENTIFIER`)
- A listener for `homekit_tv_remote_key_pressed` so Control Center D-pad keys fire IR
- Optional `binary_sensor` for real power feedback
- Optional extra `button` entities for d-pad / back / home / menu / info
- Config Flow + Options Flow (`en` and `zh-Hans`)

It does **not** talk to the TV over HDMI-CEC or a network API. It fires commands you already have in Home Assistant.

### Why the iOS Remote appears

This is the **Apple Control Center → Apple TV Remote / Remote**, not the Home Assistant Companion home-screen widget.

Home Assistant HomeKit exposes `media_player` + `device_class=tv` as HomeKit `TelevisionMediaPlayer`. The Control Center Remote appears only after:

1. The entity looks like a real HomeKit TV: `device_class=tv`, `source_list` with at least one input, `SELECT_SOURCE` in `supported_features`, plus power features if mapped.
2. You expose it via **HomeKit Bridge**. Apple requires TVs as **separate accessories** (accessory mode), not mixed in the main bridge. Pair that TV accessory in the Apple Home app **separately**.
3. You enable Control Center → Apple TV Remote / Remote.

This integration always advertises a source list (default `"TV"`) and `SELECT_SOURCE`. D-pad keys from HomeKit map to your IR/button commands.

### Make the Remote appear

**1. Copy the integration and restart**

Copy the folder `custom_components/ir_television` to `<config>/custom_components/ir_television` so that `manifest.json` is at that path. Do not flatten the package or copy the whole repository root. Then **restart Home Assistant**.

**HACS:** add this repo as a custom integration repository, download **红外电视 IR Television**, restart.

**2. Add the TV and map keys**

**Settings → Devices & Services → Add Integration → IR Television**. Map power at minimum. Map up/down/left/right/ok/back if you want the Control Center D-pad to send IR. Custom sources are optional.

**3. Expose the TV in HomeKit accessory mode**

Apple does not allow TVs on the main HomeKit bridge.

Quick path:

1. Settings → Devices & services → Add integration → **HomeKit Bridge**
2. Include `media_player` (or only this TV)
3. Finish the flow. Home Assistant creates an extra HomeKit **accessory** entry for the TV
4. Open the pairing QR / PIN on that accessory entry
5. On iPhone: **Home** app → Add Accessory → scan **that TV accessory** (not the main bridge)
6. Assign a room

Single-entity path: create a HomeKit Bridge, **before pairing** set mode to **accessory**, select only this `media_player`, then pair it in the Home app.

If the player was previously exposed as switches, remove it from HomeKit and re-add, or call `homekit.reset_accessory`.

**4. Enable Control Center Remote**

1. iPhone: **Settings → Control Center** — add **Apple TV Remote** / Remote
2. Open Control Center (swipe down from the top-right) and tap the Remote icon
3. The paired TV should be listed. Power and volume use `media_player` services; D-pad uses `homekit_tv_remote_key_pressed`.

The iPhone must be on the same LAN. The TV accessory must be paired in Home. If it only exists inside the main bridge, the Remote will **not** appear.

### Prerequisites

- Home Assistant 2024.1+
- Learned Broadlink commands **or** existing `button` entities (or both)
- [HomeKit Bridge](https://www.home-assistant.io/integrations/homekit/) for the Control Center Remote

Learn IR codes in the official Broadlink integration **first**. This component only sends them.

### Add the integration

**Settings → Devices & Services → Add Integration → IR Television**

Wizard: name → optional default Broadlink → power → optional power sensor → volume / playback / channel → navigation keys (Control Center D-pad) → optional sources.

**Configure** on the integration entry to edit later. Save reloads the entity.

### Map Broadlink / buttons

Pick **Broadlink IR**, a `remote.*` entity, the Broadlink **device** name, and the **learned command** name. Or pick **Button entity** and a `button.*` (`button.press`). You can mix both on one TV.

### Power feedback (`binary_sensor`)

Optional. Point the wizard at a `binary_sensor` that is `on` when the TV is on. Invert if reversed. Power then tracks the sensor; mute and source stay optimistic.

### Custom sources

Each source has a display name and one action. If you add none, the entity still reports `source_list: ["TV"]` with no IR action so HomeKit can create Input Source services.

---

## Development

Domain: `ir_television`  
Path: `custom_components/ir_television/`  
Version: see `manifest.json`

```text
custom_components/ir_television/
  __init__.py
  manifest.json
  const.py
  actions.py          # feature flags, HomeKit key map, validation (no HA import)
  command_sender.py
  config_flow.py
  flow_schemas.py
  media_player.py
  button.py
  diagnostics.py
  icons.json
  strings.json
  translations/en.json
  translations/zh-Hans.json
```

Syntax check (no Home Assistant install required):

```bash
python -m compileall custom_components
python -m unittest discover -s tests -v
```
