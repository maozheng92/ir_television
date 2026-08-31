# 红外电视 / IR Television

把普通红外电视变成 Home Assistant 的 **Television Media Player**（`device_class=tv`），供 **iOS 控制中心「隔空播放遥控器 / Apple TV Remote」**（HomeKit）使用。

- 图形化配置（Config Flow / Options Flow）
- 每条指令可映射 **Broadlink 红外**（`remote.send_command`）或 **按钮**（`button.press`）
- 始终暴露至少一个输入源 + `SELECT_SOURCE`（HomeKit 需要）
- 监听 `homekit_tv_remote_key_pressed`，方向键可发红外
- 可选 `binary_sensor` 作为电源状态回读

安装：把 `custom_components/ir_television/` 复制到 Home Assistant 配置目录，**重启**，再在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视**。电视必须通过 HomeKit **配件模式**单独配对后，控制中心遥控器才会出现。
