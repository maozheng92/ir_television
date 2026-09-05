# 红外电视 / IR Television

把普通红外电视变成 Home Assistant 的 **Television Media Player**（`device_class=tv`），供 **iOS 控制中心「隔空播放遥控器 / Apple TV Remote」**（HomeKit）使用。

- 图形化配置（Config Flow / Options Flow）
- 每条指令可映射 **Broadlink 红外**（`remote.send_command`）或 **按钮**（`button.press`）
- `media_player` 属性集与官方 **braviatv** 对齐（`device_class=tv`、功能位 155581、ON/OFF、`source`/`source_list`、同一组 `media_*`）
- **电视与遥控器是同一设备**：HomeKit 只暴露 `media_player`；`DeviceInfo` 不写 model（HomeKit Model = Media Player）
- 监听 `homekit_tv_remote_key_pressed`，方向键可发红外
- 可选 `binary_sensor` 作为电源状态回读

安装：把 `custom_components/ir_television/` **整个文件夹**复制到 Home Assistant 配置目录（必须包含 `translations/en.json`，不能是空文件），**重启**，再在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视**。若向导报 `en.json` 空文档，删掉该目录后重新完整拷贝。

索尼没有 AirPlay / 原厂 HomeKit：官方路径是 **Bravia 集成 → HomeKit 桥接 → HA 为电视拆出配件**。点设备上的 **按索尼方式接入 HomeKit**，把 `media_player` 加进**同一座桥**并拆出配件（不会删主桥）。家庭 App 扫配件码，不要扫主桥。
