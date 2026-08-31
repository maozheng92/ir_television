# 红外电视 / IR Television

把普通红外电视变成 Home Assistant 的 **Television Media Player**（`device_class=tv`），供 **iOS 控制中心「隔空播放遥控器 / Apple TV Remote」**（HomeKit）使用。

- 图形化配置（Config Flow / Options Flow）
- 每条指令可映射 **Broadlink 红外**（`remote.send_command`）或 **按钮**（`button.press`）
- 功能位与官方 **Sony Bravia** 电视一致（电源 / 音量 / 播放 / 输入源），HomeKit 才会建成 Television 配件
- 添加后会自动发起 **HomeKit 配件模式** 配对（索尼能出遥控器，是因为它已经有这条独立配件）
- 监听 `homekit_tv_remote_key_pressed`，方向键可发红外
- 可选 `binary_sensor` 作为电源状态回读

安装：把 `custom_components/ir_television/` 复制到 Home Assistant 配置目录，**重启**，再在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视**。重启后查看新的 HomeKit 配对通知，用 iPhone **家庭** App 扫描**这个电视配件**的二维码（不要扫主桥）。
