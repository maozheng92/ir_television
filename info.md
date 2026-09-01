# 红外电视 / IR Television

把普通红外电视变成 Home Assistant 的 **Television Media Player**（`device_class=tv`），供 **iOS 控制中心「隔空播放遥控器 / Apple TV Remote」**（HomeKit）使用。

- 图形化配置（Config Flow / Options Flow）
- 每条指令可映射 **Broadlink 红外**（`remote.send_command`）或 **按钮**（`button.press`）
- 功能位与官方 **Sony Bravia** 电视一致（`supported_features: 155581`），HomeKit 才会建成 Television 配件
- **电视与遥控器是同一设备**：HomeKit 只暴露 `media_player`，不会单独创建 remote 配件（对齐 braviatv）
- 监听 `homekit_tv_remote_key_pressed`，方向键可发红外
- 可选 `binary_sensor` 作为电源状态回读

安装：把 `custom_components/ir_television/` **整个文件夹**复制到 Home Assistant 配置目录（必须包含 `translations/en.json`，不能是空文件），**重启**，再在 **设置 → 设备与服务 → 添加集成** 中搜索 **红外电视**。若向导报 `en.json` 空文档，删掉该目录后重新完整拷贝。

把 **`media_player`** 交给现有 HomeKit（和索尼一样），删掉以前为 `remote` 多建的配件。升级后对 `media_player` 执行 `homekit.reset_accessory`，在家庭 App 里删掉旧 TCL 再扫码。控制中心遥控器请 **点顶部设备名** 从索尼切到这台电视。
