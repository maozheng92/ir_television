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
- 未配置自定义输入源时，仍会自动暴露一个默认源 **TV**，并始终带上与官方 Sony Bravia 相同的功能位（`supported_features: 155581`，含 `PLAY_MEDIA` / `BROWSE_MEDIA`）
- 当前 `source` / `volume_level` 会一直写在实体状态里，供 HomeKit `CHAR_ACTIVE_IDENTIFIER` 使用。缺当前源**不会**让控制中心遥控器消失（索尼也可以 `source: null`），只会造成家庭 App 里输入源不同步
- **`remote` 与电视是同一设备上的第二个实体**（`_attr_name = None`，无 ACTIVITY），只给 HA 自动化发红外用。**不会**单独创建 HomeKit 配件——和官方 braviatv 一样，iOS 遥控器只认 `media_player`
- 方向键由 HomeKit 事件 `homekit_tv_remote_key_pressed` 发到 `media_player`

### 为什么索尼可以显示、红外电视以前不行

这是 **系统控制中心 → 隔空播放遥控器 / Apple TV Remote**，不是 Companion 主屏幕小组件。

官方 **Sony Bravia TV** 集成会：

1. **始终**声明一整套电视功能位（含 `PLAY_MEDIA` / `BROWSE_MEDIA`），状态只有 **ON / OFF**。
2. 电视和遥控器在 HA 里是**同一设备上的两个实体**；HomeKit **只暴露 `media_player`**。不会为 `remote` 再建一条配件。
3. 你现有的 HomeKit 集成（桥接会自动把 `device_class=tv` 的播放器拆成配件，或你手动把该 `media_player` 加进配件模式）负责出现在「家庭」里。

本集成对齐上述模型：**不再自动创建 HomeKit 配置条目**。请像加索尼那样，把 **`media_player.tcl`（或你的电视实体）** 交给 HomeKit，并删掉以前多出来的「TCL 遥控器」配件。

Apple 显示遥控器仍需要：

1. 实体是 `device_class=tv` 的完整 Television（本集成现在始终如此，功能位 `155581`）。
2. 这条 **`media_player`** 已在「家庭」App 里配对（走你现有的 HomeKit 桥 / 配件，和索尼同一条路径）。
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

**3. 把 `media_player` 交给 HomeKit（和索尼同一条路径，不要给 remote 建配件）**

更新到 **1.6.0** 后：

- `remote` **不再**带 ACTIVITY，也**不会**再自动创建 HomeKit 配件
- `media_player` 功能位变为与索尼相同的 **155581**（含浏览/播放媒体）
- 设备上的「重置 HomeKit 配件」只重置 **`media_player`**

请立刻清掉以前多出来的配件：

1. HA **设置 → 设备与服务**：删除实体为 `remote.*` / 名称像 **TCL 遥控器** 的 HomeKit **配件**条目（若有）
2. 确认 HomeKit 里包含的是 **`media_player.tcl`**（和索尼一样只包含电视播放器）。若用桥接：让 `media_player` 域被包含，电视会自动拆成配件；若用配件模式：只勾选这个 `media_player`
3. 点设备上的 **重置 HomeKit 配件**，或：

```yaml
action: homekit.reset_accessory
data:
  entity_id: media_player.tcl
```

4. iPhone **家庭** App 删除旧的 TCL / 「TCL 遥控器」，再扫 **media_player 那条** HomeKit 配件的新二维码（不要扫主桥，也不要和家里原生 TCL HomeKit 电视搞混）
5. 控制中心 → 隔空播放遥控器 → **点顶部设备名**，从列表里选 TCL（默认常常还停在索尼上）

`media_player.tcl` 对齐索尼：`device_class: tv`、`source_list`、`state` 只有 on/off、`supported_features: 155581`、`assumed_state: true`。

**已经配对过但仍没有 iOS Remote Widget 时**

先看 `.storage` 里 `homekit.*.iids`。若 aid `1` 上已有：

- `D8` Television（含 `E8` RemoteKey、`E1` SleepDiscoveryMode）
- `D9_HDMI1` … `D9_HDMI4` 四个输入源
- `113` Television Speaker（音量/静音）

那 **HomeKit 配件已经是完整电视**，再改 `supported_features` 也救不了控制中心。`homekit.reset_accessory` **不会更换配对 MAC**，iPhone 上残留的 `pair verify` UUID 仍然对不上。

请更新后点设备上的 **重建 HomeKit 电视配件**（会删掉旧 HomeKit 条目并新建二维码），然后：

1. 家庭 App **每台苹果设备**都删掉 TCL / TCL 遥控器
2. 只扫 **新的** 配件二维码（不要扫主桥）
3. 家里若已有 **原厂 TCL HomeKit/AirPlay**：把本集成改名为 **TCL红外** 再点一次重建，避免同名抢发现
4. 用 Discovery 看 `_hap._tcp`：`ci` 必须是 **31**；配对成功后 `sf` 必须是 **0**
5. 控制中心遥控器 **点顶部设备名** 选这台（默认常停在索尼上）

### 如何读 `_hap._tcp` mDNS

```text
TCL 6D29D3._hap._tcp.local.
c# = 2
ci = 31
ff = 0
id = 8E:CB:0F:6D:29:D3
md = TCL
pv = 1.1
s# = 1
sf = 0
```

| 字段 | 含义 |
| --- | --- |
| `ci` | HAP 配件类别（只影响图标/分组，不改变 Television 服务本身）：**24 = Apple TV**，**31 = Television**（官方 HomeKit / pyhap / HAP-NodeJS）。HA 的 `TelevisionMediaPlayer` 广播的就是 **31**，这是对的。不要改成 24。 |
| `ci = 31` | 这条配件是 **Television**。实体 / HomeKit 侧已经做对了。 |
| `sf = 1` | **未配对**。控制中心遥控器不会列出。 |
| `sf = 0` | **已配对**。HAP 广播已经允许 iOS 把它当作电视遥控器。若控制中心仍没有，是 iOS 选错设备或和原厂 TCL/索尼 AirPlay 同名，不是缺 Television 服务。 |
| `md = TCL` | 广播名称。家里已有原厂 TCL 时，控制中心列表里可能有两个 TCL，默认停在原厂/索尼上。 |
| `id` | 这条 HA 配件的身份。家庭 App 里的 TCL 必须对应这个 `id`。 |

`sf = 0` 且 `ci = 31` 之后请：

1. 打开 **家庭** App，确认这台 TCL 是 **电视图标**（能开关、切 HDMI），不是开关/网桥
2. iPhone **设置 → 控制中心** 已加入 **隔空播放遥控器**
3. 打开遥控器后 **点最上方设备名**，在列表里选 HA 这台（不要选索尼，也不要选原厂 TCL）
4. 若列表里根本没有：把本集成改名为 **TCL红外** 再重建配件，避免 `md = TCL` 和原厂抢名字

索尼能出现在「隔空播放遥控器」里，经常是电视自己的 **AirPlay 2**，不是 HA `braviatv`。红外电视没有 AirPlay，只能靠这条已配对的 HomeKit 电视配件。

**4. 打开控制中心遥控器**

1. iPhone：**设置 → 控制中心**，确保已加入 **隔空播放遥控器** / **遥控器** / Apple TV Remote
2. 从屏幕右上角下滑打开控制中心，点遥控器图标
3. 应能看到刚配对的那台电视。电源、音量走 `media_player`；方向键走本集成的 HomeKit 事件

同一局域网；电视配件必须已在「家庭」中配对。主桥里有这台电视、配件模式未配对时，遥控器**不会**出现。

### 日志出现 `attempted pair verify without being paired first`

这是 **HomeKit 配对记录和 iPhone 对不上**，不是红外码错误。配件名 **TCL** 表示 HA 正在用 pyhap 广播这条电视配件。

含义：若干苹果设备（日志里的 `192.168.1.x`）带着同一个控制器 UUID 来做「已配对验证」，但 HA 这份配件的已配对列表里**没有**这个 UUID。常见原因：

- 重建过 HomeKit 配件 / 重启后换了新条目，家庭 App 里还留着旧 TCL
- 家里已有一台原生 HomeKit 的 TCL 电视，和 HA 里这台红外电视**同名**，iOS 连错了
- 一台 iPhone 扫过码，其它设备靠 iCloud 同步失败，却仍在尝试连接

按这个清干净再配一次（和第一次加索尼配件一样）：

1. iPhone **家庭** App：删除所有叫 TCL / 红外电视 的配件（每台 iPhone、iPad 都看一眼）
2. HA **设置 → 设备与服务**：只保留**一条**包含这台 **`media_player.*`** 的 HomeKit（桥接拆出的电视配件，或配件模式且只勾了播放器）。删掉 `remote.*` 的多余配件
3. 打开这条 HomeKit 的 **配对二维码**，用**一台** iPhone 添加配件（不要扫主桥）
4. 其它设备等「家庭」iCloud 同步，不要各自再扫码
5. 若提示无法添加：删掉该 HomeKit 配件条目 → 重启 HA → 用新二维码再配

配对成功后这条 `pair verify` 日志应停止。若还在刷，就是某台苹果设备仍握着旧配对，在那台设备的家庭 App 里把 TCL 删掉。

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

### 向导报 `en.json` 空文件 / 无法加载配置向导

日志若出现 `translations/en.json: Input is a zero-length, empty document`，说明 **HA 配置目录里这份文件是 0 字节**，不是仓库缺文件。Home Assistant 打开配置向导时会强制解析该 JSON，空文件会直接失败。

请 **删掉整个** `/config/custom_components/ir_television/` 后再拷一次（不要只拷 `.py`、不要先建空文件再粘贴）：

```text
/config/custom_components/ir_television/manifest.json
/config/custom_components/ir_television/strings.json
/config/custom_components/ir_television/translations/en.json
/config/custom_components/ir_television/translations/zh-Hans.json
```

在 HA **文件编辑器**里打开 `translations/en.json`，开头必须是 `{`，体积大约十几 KB，不能是空白。Samba / 从 Mac 拷目录时偶尔会留下 0 字节占位文件，遇到就删掉重拷。然后 **完整重启** Home Assistant，再添加集成。

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

- A `media_player` (`MediaPlayerDeviceClass.TV`) with the same feature bits as official **Sony Bravia** (`supported_features: 155581`, including `PLAY_MEDIA` / `BROWSE_MEDIA`). State is **ON or OFF** only
- A `remote` on the **same device** (`_attr_name = None`, no ACTIVITY) for `remote.send_command`. HomeKit does **not** get a second accessory — same as braviatv
- A default **TV** input source when you configured none
- A listener for `homekit_tv_remote_key_pressed` so Control Center D-pad keys fire IR
- Optional `binary_sensor` for real power feedback
- Optional diagnostic `button` entities for d-pad / back / home / menu / info (hidden from HomeKit)
- Config Flow + Options Flow (`en` and `zh-Hans`)

It does **not** talk to the TV over HDMI-CEC or a network API. It fires commands you already have in Home Assistant. It does **not** auto-create HomeKit config entries; include the `media_player` in your existing HomeKit setup the same way as Sony.

### Why Sony shows in the iOS Remote and this TV did not

This is the **Apple Control Center → Apple TV Remote / Remote**, not the Home Assistant Companion home-screen widget.

Official **Sony Bravia TV** advertises a full Television feature set on **one** `media_player`. The HA `remote` entity is unnamed, has no ACTIVITY flag, and is **not** a HomeKit accessory. HomeKit (bridge auto-split or accessory include) exposes only that media player.

Include **`media_player.*`** in HomeKit. Delete any extra accessory that was created for `remote.*` / “TCL 遥控器”. After upgrading, `homekit.reset_accessory` on the media player (feature bits changed to 155581), delete the old Home accessory, re-scan, then tap the **title** in Control Center Remote to switch from Sony to this TV.

### Make the Remote appear

**1. Copy the integration and restart**

Copy the folder `custom_components/ir_television` to `<config>/custom_components/ir_television` so that `manifest.json` is at that path. Do not flatten the package or copy the whole repository root. Then **restart Home Assistant**.

**HACS:** add this repo as a custom integration repository, download **红外电视 IR Television**, restart.

**2. Add the TV and map keys**

**Settings → Devices & Services → Add Integration → IR Television**. Map power at minimum. Map up/down/left/right/ok/back if you want the Control Center D-pad to send IR. Custom sources are optional.

**3. Pair the HomeKit *media_player* (not the remote)**

Sony does not create a separate HomeKit accessory for its remote. Include `media_player.tcl` in HomeKit the same way. Delete leftover accessory-mode entries for `remote.*`. Then:

```yaml
action: homekit.reset_accessory
data:
  entity_id: media_player.tcl
```

Delete TCL in the Home app, scan the **media_player** accessory QR, and in Control Center Remote tap the **top device name** to pick this TV (it often stays on Sony).

**4. Enable Control Center Remote**

1. iPhone: **Settings → Control Center** — add **Apple TV Remote** / Remote
2. Open Control Center (swipe down from the top-right) and tap the Remote icon
3. The paired TV should be listed. Power and volume use `media_player` services; D-pad uses `homekit_tv_remote_key_pressed`.

The iPhone must be on the same LAN. The TV accessory must be paired in Home. If it only exists inside the main bridge, the Remote will **not** appear.

### Log: `attempted pair verify without being paired first`

This is a **stale HomeKit pairing**, not a bad IR mapping. An Apple device is trying to verify a pairing UUID that this HA accessory does not have. Remove TCL from the Home app on every iPhone/iPad, keep a single HomeKit **accessory** entry for this `media_player`, and pair with one iPhone's QR code. Other devices must join via iCloud Home sharing, not a second scan.

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
  remote.py           # same device, no ACTIVITY, not a HomeKit accessory
  homekit_expose.py   # rebuild HomeKit accessory with a new pairing identity
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
