# Docker / ModelScope 部署

本 fork 在根目录提供可直接构建的 `Dockerfile` 和 `compose.yaml`。基础镜像固定为
`bgzerol/starrailcopilot:slim` 当前的 linux/amd64 内容摘要；镜像只提供 Python 3.10、
ADB、Git 和运行依赖，容器中的应用源码会被本 fork 当前版本完整替换。

## Docker Compose

```bash
cp .env.docker.example .env
# 编辑 .env，为 SRC_WEBUI_PASSWORD 设置强密码
docker compose up -d --build
```

浏览器访问 `http://127.0.0.1:22367`。运行数据保存在 `data/config` 和 `data/log`，
不会写回 Git。

## ModelScope

ModelScope 使用根目录 `Dockerfile`，业务端口为 `22367`，启动命令为
`/usr/local/bin/starrail-entrypoint`。部署时必须把 `SRC_WEBUI_PASSWORD` 作为 Studio
Secret 配置，不能写进 Dockerfile、Compose 或仓库变量。

ModelScope 只运行 SRC Web 管理端和调度器，不提供安卓模拟器。真正执行游戏任务前，
仍需在 SRC 中配置一台该容器能够通过 ADB 访问的安卓设备或云手机。

Compose 的宿主机卷可以持久化配置；ModelScope Studio 是否持久化容器目录取决于平台
实际存储策略，本仓库不把 `/app/config` 的跨重建保留当作平台保证。

## 基础镜像来源

- Docker Hub：<https://hub.docker.com/r/bgzerol/starrailcopilot>
- 固定摘要：`sha256:fb3cc1d3d180f381c81e5a05683782fbbf02590613abf5f59c65b2f12762745f`
- 镜像平台：`linux/amd64`

更新基础镜像时先检查镜像配置仍为 `/app`、Python 3.10，并验证 `python`、`git`、
`adb` 三个命令存在，再更新 `Dockerfile`、`compose.yaml` 和 `.env.docker.example`
中的摘要。
