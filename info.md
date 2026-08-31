# 红外电视 / IR Television

把普通红外电视变成 Home Assistant 的 **Television Media Player**（`device_class=tv`），供 **iOS Companion 遥控器小组件** 使用。

- 图形化配置（Config Flow / Options Flow）
- 每条指令可映射 **Broadlink 红外**（`remote.send_command`）或 **按钮**（`button.press`）
- 可自定义输入源
- 可选 `binary_sensor` 作为电源状态回读

安装后重启 Home Assistant，在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视**。
