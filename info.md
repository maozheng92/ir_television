# 红外电视 / IR Television

把普通红外电视变成 Home Assistant 的 **Television Media Player**（`device_class=tv`），经 HomeKit 桥接出现在「家庭」App。控制中心遥控器的设备列表由 iOS / 中枢收录；若列表里的 SONY 不是 HA 配件，本集成无法把红外电视写进那个列表。

- 图形化配置（Config Flow / Options Flow）
- 每条指令可映射 **Broadlink 红外**（`remote.send_command`）或 **按钮**（`button.press`）
- `media_player` 属性集与官方 **braviatv** 对齐（`device_class=tv`、功能位 155581、ON/OFF、`source`/`source_list`、同一组 `media_*`）
- **电视与遥控器是同一设备**：HomeKit 只暴露 `media_player`；`DeviceInfo` 不写 model（HomeKit Model = Media Player）
- 监听 `homekit_tv_remote_key_pressed`，方向键可发红外
- 可选 `binary_sensor` 作为电源状态回读

安装：把 `custom_components/ir_television/` **整个文件夹**复制到 Home Assistant 配置目录（必须包含 `translations/en.json`，不能是空文件），**重启**，再在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视**。若向导报 `en.json` 空文档，删掉该目录后重新完整拷贝。

家庭 App 扫配件模式二维码（不要扫主桥）。不要为进控制中心列表而反复重建配对。若遥控器里只有 SONY + Apple TV，且去掉 HA 索尼配件后红外电视仍不出现，那是 iOS 设备池，不是本集成还能改的实体字段。
