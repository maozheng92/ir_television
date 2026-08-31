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
- 未配置自定义输入源时，仍会自动暴露一个默认源 **TV**，并始终带上完整的 Sony Bravia 式功能位（开/关、音量、播放、输入源），HomeKit 才能建成 Television + Speaker
- 添加或重启后会**自动创建 HomeKit 配件模式条目**（索尼能出遥控器，是因为它在配置 HomeKit 时已经有这条独立配件；后加的红外电视以前会被主桥跳过）
- 方向键、返回、主页、菜单、信息：配置后会出现诊断类 `button`（不进 HomeKit）；**同时**监听 `homekit_tv_remote_key_pressed`

### 为什么索尼可以显示、红外电视以前不行

这是 **系统控制中心 → 隔空播放遥控器 / Apple TV Remote**，不是 Companion 主屏幕小组件。

官方 **Sony Bravia TV** 集成会：

1. **始终**声明一整套电视功能位（`TURN_ON/OFF`、`VOLUME_STEP/MUTE/SET`、`PLAY/PAUSE`、`SELECT_SOURCE` 等），HomeKit 据此创建 Television 配件。
2. 在第一次配置 HomeKit 并勾选 `media_player` 域时，自动得到一条 **配件模式** 条目，再在「家庭」里单独配对。

红外电视如果是后来才加的，HomeKit **不会**再为它建配件（主桥还会把电视排除掉），所以控制中心没有遥控器。本版本会自己发起与索尼相同的配件配对流程，并把功能位对齐索尼。

Apple 显示遥控器仍需要：

1. 实体是 `device_class=tv` 的完整 Television（本集成现在始终如此）。
2. 在「家庭」App 里**单独配对**这条电视配件（不要只配对主桥）。
3. iPhone：**设置 → 控制中心** 打开 **隔空播放遥控器 / 遥控器**。

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

**3. 配对 HomeKit 电视配件（和索尼一样，必须单独扫码）**

更新本集成并**完整重启**后，会自动出现一条新的 **HomeKit 配件**（设置 → 设备与服务里多一个 HomeKit 条目，名称是这台电视）。

1. 打开该 HomeKit 条目上的 **配对二维码 / PIN**
2. iPhone **家庭** App → 添加配件 → 扫描**这个电视配件**（**不要**扫「Home Assistant Bridge」主桥，索尼也是单独那条）
3. 放进房间并完成设置
4. 若以前把这台 `media_player` 当开关加进过主桥：在家庭 App 里删掉旧设备，并在 HA 里删掉旧 HomeKit 配件后重启，让本集成重建

自动创建失败时，前端会有持久通知。手动做法：添加 **HomeKit 桥接** → 配对前改成 **配件 (accessory)** → 只选这台 `media_player.*`。

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

- A `media_player` (`MediaPlayerDeviceClass.TV`) with the same core feature bits as official **Sony Bravia** (`TURN_ON/OFF`, volume step/mute/set, play/pause, `SELECT_SOURCE`)
- A default **TV** input source when you configured none
- Automatic **HomeKit accessory-mode** pairing (Sony appears in Control Center because it already has that standalone accessory; a TV added later used to be skipped)
- A listener for `homekit_tv_remote_key_pressed` so Control Center D-pad keys fire IR
- Optional `binary_sensor` for real power feedback
- Optional diagnostic `button` entities for d-pad / back / home / menu / info (hidden from HomeKit)
- Config Flow + Options Flow (`en` and `zh-Hans`)

It does **not** talk to the TV over HDMI-CEC or a network API. It fires commands you already have in Home Assistant.

### Why Sony shows in the iOS Remote and this TV did not

This is the **Apple Control Center → Apple TV Remote / Remote**, not the Home Assistant Companion home-screen widget.

Official **Sony Bravia TV** always advertises a full Television feature set, and HomeKit created an **accessory-mode** entry when the bridge was first set up with the `media_player` domain. TVs added later are excluded from the bridge and never get a pairing QR — so Control Center never lists them. This integration now starts that same accessory flow and matches Sony's feature bits.

You still need to:

1. Pair **that TV accessory** in the Apple Home app (not the main HA bridge).
2. Enable Control Center → Apple TV Remote / Remote.

### Make the Remote appear

**1. Copy the integration and restart**

Copy the folder `custom_components/ir_television` to `<config>/custom_components/ir_television` so that `manifest.json` is at that path. Do not flatten the package or copy the whole repository root. Then **restart Home Assistant**.

**HACS:** add this repo as a custom integration repository, download **红外电视 IR Television**, restart.

**2. Add the TV and map keys**

**Settings → Devices & Services → Add Integration → IR Television**. Map power at minimum. Map up/down/left/right/ok/back if you want the Control Center D-pad to send IR. Custom sources are optional.

**3. Pair the HomeKit TV accessory**

After restart, a new **HomeKit accessory** entry appears (named after this TV). Open its pairing QR / PIN. On iPhone: **Home** → Add Accessory → scan **that accessory** (not the main bridge — same as Sony). If this `media_player` was previously exposed as switches, delete the old Home accessory and the old HomeKit entry, then restart so it can be recreated.

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
  homekit_expose.py   # starts HomeKit accessory-mode pairing
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
