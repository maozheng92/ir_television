# 红外电视 / IR Television

把普通红外电视变成 Home Assistant 的 **Television Media Player**（`device_class=tv`），供 **iOS 控制中心「隔空播放遥控器 / Apple TV Remote」**（HomeKit）使用。

- 图形化配置（Config Flow / Options Flow）
- 可自定义 **生产企业**（写入设备和 HomeKit 配件信息）
- 输入源可在配置里 **拖拽排序**（顺序即 HA / HomeKit 显示顺序）
- 电源默认为 **单个电源键**（实体行上一个开关，开/关发同一条指令）
- 每条指令可映射 **Broadlink 红外**（`remote.send_command`）或 **按钮**（`button.press`）
- 按钮可 **多选并按顺序执行**，每个按钮可重复按，并可设置按键间隔
- `media_player` 属性集与官方 **braviatv** 对齐（`device_class=tv`、功能位 155581、ON/OFF、`source`/`source_list`、同一组 `media_*`）
- **电视与遥控器是同一设备**：HomeKit 只暴露 `media_player`；`DeviceInfo` 不写 model（HomeKit Model = Media Player）
- 监听 `homekit_tv_remote_key_pressed`，方向键可发红外
- 可选 `binary_sensor` 作为电源状态回读
- 自带集成图标（`brand/` + 仓库根目录 `icon.png`）

仓库：https://github.com/maozheng92/ir_television  

安装：把 `custom_components/ir_television/` **整个文件夹**复制到 Home Assistant 配置目录（必须包含 `translations/en.json`，不能是空文件），**重启**，再在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视**。HACS 把上述仓库加为 Integration 自定义仓库即可。若向导报 `en.json` 空文档，删掉该目录后重新完整拷贝。

索尼没有 AirPlay / 原厂 HomeKit：官方路径是 **Bravia 集成 → HomeKit 桥接 → HA 为电视拆出配件**。点设备上的 **按索尼方式接入 HomeKit**，把 `media_player` 加进**同一座桥**并拆出配件（不会删主桥）。家庭 App 扫配件码，不要扫主桥。
