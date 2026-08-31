# IR Television / 红外电视

Home Assistant 自定义集成：把普通红外电视变成 **Television Media Player**（`device_class=tv`），可在 **iOS Home Assistant Companion 遥控器小组件** 和 App 内 Remote 里使用。每条按键或输入源可以走 **Broadlink 红外**（`remote.send_command`）或任意 **按钮实体**（`button.press`）。图形化 Config Flow / Options Flow，无需 YAML。

A Home Assistant custom integration that exposes a dumb IR television as a **Television Media Player** (`device_class=tv`) so the **iOS Companion Remote widget** (and in-app Remote) can control it. Each key or input source is either **Broadlink IR** (`remote.send_command`) or a **button entity** (`button.press`). Setup is a graphical wizard — no YAML required.

---

## 中文

### 它是什么

- 平台：`media_player`，设备类别 `tv`（iOS 遥控器小组件只认这类实体）
- 电源状态：默认乐观 / 假定；可选用 `binary_sensor` 作为真实开关回读（智能插座、电流钳、HDMI-CEC、模板等）
- 可自定义输入源（HDMI 1、HDMI 2、电视、Netflix…）
- 方向键、返回、主页、菜单、信息：配置后会出现在**同一设备**上的额外 `button` 实体，方便仪表盘；**iOS 小组件只用下面的 media_player 功能**

### 为什么 iOS 遥控器小组件能用

Companion 的 Remote Widget / 控制中心遥控器会寻找：

1. `media_player` 且 `device_class = tv`
2. `supported_features` 里实际配置过的功能（未映射的按钮会隐藏）

本集成会按你映射的指令动态计算功能位：

| 功能 | 需要映射的指令 |
| --- | --- |
| 开 / 关 | `turn_on` / `turn_off`，或单独的 `power_toggle`（开、关、切换都走这一键） |
| 音量加减 | `volume_up` / `volume_down` |
| 静音 | `volume_mute`（切换；本地保留静音标志） |
| 播放 / 暂停 | `play`、`pause`，或只有一个 `play_pause`（三者都映射到它） |
| 停止 | `stop`（可选） |
| 下一首 / 上一首 | `next_track` / `previous_track`（频道加减或切歌） |
| 选择输入源 | 至少一个自定义源 |

### 前提条件

- Home Assistant 2024.1 或更新（自定义组件目录 + Config Flow）
- **二选一或混用：**
  - 官方 [Broadlink](https://www.home-assistant.io/integrations/broadlink/) 集成，并且已经**学习好**电视红外码；或
  - 已有的 `button.*` 实体（例如 helper、其他红外/射频集成、脚本按钮）

**请先在 Broadlink 集成里学习红外**，再添加本集成。本集成不会学习红外，只会调用 `remote.send_command`。

### 安装

安装完成后必须**重启 Home Assistant**，然后在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视** 或 **IR Television**。

**HACS（推荐）**

1. HACS → 右上角 ⋮ → Custom repositories
2. 填入此仓库地址，类别选 Integration
3. 搜索 **红外电视** 或 **IR Television** 并下载
4. **重启** Home Assistant

**手动安装**

把仓库里的 **`custom_components/ir_television` 整个文件夹** 复制到 Home Assistant 配置目录：

```text
<config>/custom_components/ir_television/manifest.json
```

Home Assistant OS / Container 上一般是：

```text
/config/custom_components/ir_television/manifest.json
```

复制的是内层 `ir_television` 文件夹，不要把整个仓库根目录丢进去（否则会多一层目录，集成不会出现）。

**添加后仍搜不到时**

1. 确认 `manifest.json` 就在 `custom_components/ir_television/` 下，且 `"domain": "ir_television"`
2. 完整重启一次（仅重新加载前端不够）
3. 搜索 **红外电视**、**IR Television** 或 **ir_television**
4. 设置 → 系统 → 日志，查找 `ir_television`
5. 浏览器强制刷新或无痕窗口

### 添加集成

1. **设置 → 设备与服务 → 添加集成**
2. 搜索 **IR Television** / **红外电视**
3. 按向导操作：
   1. 给电视起名
   2. （可选）选择默认 Broadlink `remote.*` 和设备名
   3. 电源：独立开关，或单键切换
   4. （可选）选择一个 `binary_sensor` 作为电源状态回读
   5. 音量 / 静音、播放、频道
   6. （可选）方向键与菜单 → 额外按钮实体
   7. 循环添加输入源，完成后结束

之后可在集成卡片上点 **配置** 修改名称、指令和源（无需删除重建）。保存后会自动重新加载实体。

### 如何映射 Broadlink

1. 在官方 Broadlink 集成中学习按键，记住 **设备名** 和 **指令名**
2. 本集成里控制方式选 **Broadlink 红外**
3. 选择 `remote.xxx`（或使用向导里的默认遥控器）
4. 填写设备名（官方集成通常需要）和指令名，例如 `power_on`、`hdmi_1`
5. 运行时调用：

```yaml
service: remote.send_command
data:
  entity_id: remote.xxx
  device: living_room_tv   # 可选，不用可省略
  command: power_on
  num_repeats: 1
```

Broadlink 实体暂时不可用时，本集成**不会崩溃**，只会在日志里写警告。

### 如何映射按钮

1. 控制方式选 **按钮实体**
2. 选择任意 `button.*`
3. 运行时调用 `button.press`

同一台电视可以混用：电源走红外，某个输入源走按钮。

### 用 binary_sensor 做状态回读

红外电视默认没有电源反馈。如果你有一个能反映电视是否开机的 `binary_sensor`（例如测量电视插头的电流/功率、HDMI-CEC 电源、或模板二进制传感器），可以在向导里把它指定为**电源状态传感器**：

- 传感器 `on` → 电视开机；`off` → 电视关机
- 若逻辑相反（`on` 表示关机），勾选**反转**
- 配置后，该 `media_player` 的电源不再是假定状态；传感器变化会立刻更新实体
- 发送开/关指令后仍会先乐观更新，随后以传感器为准纠正（红外没打到时会自动回到真实状态）
- 音量、播放、切源在配置了传感器时**不会**再把电视假定为开机
- 传感器为 `unavailable` / `unknown` 时保留上一次明确状态，媒体播放器仍可控制
- 清空该字段即恢复假定开关。静音和当前输入源仍是本地乐观状态

之后可在集成 **配置 → 电源状态传感器** 中修改或移除。

### 自定义输入源

每个源包含：

- **显示名称**（`source_list` 和 iOS 源选择器）
- **动作**：Broadlink 或按钮

选择源会发送对应指令，并乐观更新当前 `source`。名称会去空格，不能为空，不能重复。

示例：`HDMI 1`、`HDMI 2`、`TV`、`Netflix`。

### 在 iOS Companion 里使用

1. 用 iPhone 打开 Home Assistant Companion
2. 确认能看到这台 `media_player`（设备类别为电视）
3. 主屏幕添加 **Home Assistant Remote** 小组件，或在控制中心加入遥控器，选中这个媒体播放器
4. 小组件上的电源、音量、静音、播放/暂停、频道、源选择会调用标准 `media_player` 服务

方向键请用仪表盘上的额外按钮，或 App 内其它卡片。iOS 小组件**不会**使用那些导航按钮。

### 控制后端说明

| 方式 | 服务 | 需要填写 |
| --- | --- | --- |
| Broadlink / 任意 remote | `remote.send_command` | `entity_id`、`command`，可选 `device`、`num_repeats` |
| 按钮 | `button.press` | `entity_id` |

未映射的功能不会出现在 `supported_features` 里。调用未映射的服务会记录警告并忽略。

---

## English

### What it is

A HACS-ready custom component (`custom_components/ir_television`) that creates one TV device with:

- A `media_player` (`MediaPlayerDeviceClass.TV`)
- Optional `binary_sensor` for real power feedback (otherwise assumed on/off)
- Optional extra `button` entities for d-pad / back / home / menu / info
- Config Flow + Options Flow (`en` and `zh-Hans`)

It does **not** talk to the TV over HDMI-CEC or a network API. It fires commands you already have in Home Assistant.

### Why the iOS Remote widget works

The Companion Remote widget looks for a `media_player` with `device_class=tv` and standard features (`TURN_ON` / `TURN_OFF`, `VOLUME_STEP`, `VOLUME_MUTE`, `PLAY` / `PAUSE`, `NEXT_TRACK` / `PREVIOUS_TRACK`, `SELECT_SOURCE`). This integration advertises **only** the features you actually mapped, so unused widget buttons stay hidden.

Assumed on/off (and mute / source) updates when a command is sent. After a restart, the last state is restored if Home Assistant still has it. If you assign a power `binary_sensor`, power follows that sensor instead (`assumed_state` is then false for this entity).

### Prerequisites

- Home Assistant 2024.1+
- Learned Broadlink commands **or** existing `button` entities (or both)

Learn IR codes in the official Broadlink integration **first**. This component only sends them.

### Install

**HACS:** add this repo as a custom integration repository, download **红外电视 IR Television**, restart.

**Manual:** copy the folder `custom_components/ir_television` to `<config>/custom_components/ir_television` so that `manifest.json` is at that path. Do not copy the whole repository root into `custom_components/`.

If it does not show up: confirm that path, restart Core, search **红外电视** / **IR Television**, and check the log for `ir_television`.

### Add the integration

**Settings → Devices & Services → Add Integration → IR Television**

Wizard:

1. Name the TV  
2. Optional default Broadlink `remote.*` + device name  
3. Power (on/off or one toggle key)  
4. Optional power `binary_sensor`  
5. Volume / mute, playback, channel  
6. Optional navigation keys (extra buttons, not the iOS widget)  
7. Add sources in a loop  

**Configure** on the integration entry to edit later. Save reloads the entity.

### Map Broadlink

Pick **Broadlink IR**, a `remote.*` entity, the Broadlink **device** name, and the **learned command** name. Official Broadlink almost always needs the device name.

### Map buttons

Pick **Button entity** and a `button.*`. The integration calls `button.press`.

### Power feedback (`binary_sensor`)

Optional. Point the wizard at a `binary_sensor` that is `on` when the TV is on (smart plug / current clamp / HDMI-CEC / template). Invert if the logic is reversed. Power then tracks the sensor instead of assumed state; mute and source stay optimistic. Clear the field to return to assumed on/off.

### Custom sources

Each source has a display name and one action (IR or button). Selecting it sends the action and sets `source` optimistically. Names are trimmed; empty and duplicate names are rejected.

Example list: HDMI 1, HDMI 2, TV, Netflix.

### iOS Companion Remote widget

Add the Home Assistant Remote widget (or Control Center remote) and pick this media player. Power, volume, mute, play/pause, next/previous, and source use `media_player` services. D-pad keys are dashboard buttons only.

### After install checklist

1. Learn IR in Broadlink (or create buttons)  
2. Install this folder under `custom_components/`  
3. Restart Home Assistant  
4. Add **IR Television** and map keys / sources  
5. On iPhone, point the Remote widget at the new TV media player  

---

## Development

Domain: `ir_television`  
Path: `custom_components/ir_television/`

```text
custom_components/ir_television/
  __init__.py
  manifest.json
  const.py
  actions.py          # feature flags & validation (no Home Assistant import)
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
