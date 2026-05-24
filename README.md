---
title: StarRailCopilot
emoji: 🚆
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

**| [English](README_en.md) | 简体中文 | [Español](README_es.md) | [日本語](README_ja.md) |**


# StarRailCopilot

Star Rail auto script | 星铁速溶茶，崩坏：星穹铁道脚本，基于下一代Alas框架。

## Hugging Face Spaces Docker 部署

本分支包含 Hugging Face Docker Space 所需的 `Dockerfile`、`.dockerignore`、`docker-constraints.txt` 和 `hf_space_entrypoint.py`。Space 会通过 README front matter 使用 `sdk: docker`，并把 WebUI 暴露到 `app_port: 7860`。

部署到 Hugging Face Spaces 时建议使用一个轻量 Space 仓库从本分支构建。容器启动时会自动生成 `config/deploy.yaml`，关闭自动更新、自动安装依赖、ADB 替换和自动连接，并强制监听 `0.0.0.0:${PORT:-7860}`。

持久化说明：

- 如果 Space 已挂载 Hugging Face Persistent Storage，容器会使用 `/data/starrailcopilot/config`、`/data/starrailcopilot/log` 和 `/data/starrailcopilot/screenshots` 保存运行数据。
- 首次启动会把镜像内置的 `config` 模板复制到持久化目录，再把 `/app/config`、`/app/log`、`/app/screenshots` 链接到 `/data/starrailcopilot/*`。
- 如果没有挂载 Persistent Storage，则回退到镜像内的临时目录；Space 重建或重启后运行配置和日志可能丢失。

可选配置：

- `SRC_WEBUI_PASSWORD`：设置为 Space Secret 后启用 WebUI 密码。
- `SPACE_PASSWORD`：兼容备用密码变量，优先级低于 `SRC_WEBUI_PASSWORD`。

限制说明：Hugging Face Spaces 不能运行 Windows 模拟器，也不适合直接托管游戏客户端。本 Docker Space 版本用于启动 SRC WebUI；实际自动化仍需要可从容器访问的 Android/ADB 或云游戏环境。

![gui](https://raw.githubusercontent.com/wiki/LmeSzinc/StarRailCopilot/README.assets/gui_cn.png)

![setting](https://raw.githubusercontent.com/wiki/LmeSzinc/StarRailCopilot/README.assets/setting_cn.png)

## 功能

- **打本**：[角色养成规划](https://github.com/LmeSzinc/StarRailCopilot/wiki/Planner_cn)，每日副本，双倍活动副本，历战余响。
- **收获**：完成每日任务，收派委托，收取无名勋礼奖励。
- **模拟宇宙**：刷模拟宇宙，使用开拓力刷内圈遗器。
- **后台托管**：自动启动模拟器和游戏，后台托管清体力和每日，通过仪表盘了解资源情况。
- **云游戏**：（仅国服）[在云崩坏星穹铁道上运行SRC](https://github.com/LmeSzinc/StarRailCopilot/wiki/Cloud_cn)

## 安装 [![](https://img.shields.io/github/downloads/LmeSzinc/StarRailCopilot/total?color=4e4c97)](https://github.com/LmeSzinc/StarRailCopilot/releases)

[中文安装教程](https://github.com/LmeSzinc/StarRailCopilot/wiki/Installation_cn)，包含自动安装教程，使用教程，手动安装教程。

[设备支持文档](https://github.com/LmeSzinc/AzurLaneAutoScript/wiki/Emulator_cn)，支持 Windows/Mac/Linux 以及各种骚方式运行。

> **为什么使用模拟器？** 如果你用桌面端来运行脚本的话，游戏窗口必须保持在前台，我猜你也不想运行脚本的时候不能动鼠标键盘像个傻宝一样坐在那吧，所以用模拟器。

> **模拟器的性能表现如何？** Lme 的 8700k+1080ti 使用 MuMu 12 模拟器画质设置非常高是有 40fps 的，如果你的配置稍微新一点的话，特效最高 60fps 不是问题。

## 开发

QQ一群 752620927 (有开发意向请加一群)
QQ二群 1033583803
Discord https://discord.gg/aJkt3mKDEr

- [小地图识别原理](https://github.com/LmeSzinc/StarRailCopilot/wiki/MinimapTracking)
- 开发文档（目录在侧边栏）：[Alas wiki](https://github.com/LmeSzinc/AzurLaneAutoScript/wiki/1.-Start)，但很多内容是新写的，建议阅读源码和历史提交。
- 开发路线图：见置顶 issue，欢迎提交 PR，挑选你感兴趣的部分进行开发即可。

> **如何添加多语言/多服务器支持？** 需要适配 assets，参考 [开发文档 “添加一个 Button” 一节](https://github.com/LmeSzinc/AzurLaneAutoScript/wiki/4.1.-Detection-objects#%E6%B7%BB%E5%8A%A0%E4%B8%80%E4%B8%AA-button)。

## 关于 Alas

SRC 基于碧蓝航线脚本 [AzurLaneAutoScript](https://github.com/LmeSzinc/AzurLaneAutoScript) 开发，Alas 经过三年的发展现在已经达到一个高完成度，但也累积了不少屎山难以改动，我们希望在新项目上解决这些问题。

- 更新 OCR 库。Alas 在 cnocr==1.2.2 上训练了多个模型，但依赖的 [mxnet](https://github.com/apache/mxnet) 已经不怎么活跃了，机器学习发展迅速，新模型的速度和正确率都碾压旧模型。
- 配置文件 [pydantic](https://github.com/pydantic/pydantic) 化。自任务和调度器的概念加入后用户设置数量倍增，Alas 土制了一个代码生成器来完成配置文件的更新和访问，pydantic 将让这部分更加简洁。
- 更好的 Assets 管理。button_extract 帮助 Alas 轻易维护了 4000+ 模板图片，但它有严重的性能问题，对外服缺失 Assets 的提示也淹没在了大量垃圾 log 中。
- 减少对于碧蓝的耦合。Alas 框架和 Alas GUI 有对接其他游戏及其脚本的能力，但已经完成的明日方舟 [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) 插件和正在开发的 [fgo-py](https://github.com/hgjazhgj/FGO-py) 插件都发现了 Alas 与碧蓝航线游戏本身耦合严重的问题。

