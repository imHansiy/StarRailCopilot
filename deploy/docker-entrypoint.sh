#!/bin/sh
set -eu

cd /app

if [ -z "${SRC_WEBUI_PASSWORD:-}" ]; then
  echo "SRC_WEBUI_PASSWORD 未配置，拒绝启动公开管理界面" >&2
  exit 64
fi

port="${PORT:-22367}"
mkdir -p /app/config /app/log

if [ ! -f /app/config/deploy.yaml ]; then
  python -m deploy.set \
    Repository=global \
    Branch=master \
    GitExecutable=git \
    AutoUpdate=false \
    PythonExecutable=python \
    InstallDependencies=false \
    AdbExecutable=adb \
    ReplaceAdb=false \
    AutoConnect=false \
    EnableReload=false \
    CheckUpdateInterval=0 \
    AutoRestartTime=null \
    WebuiHost=0.0.0.0 \
    WebuiPort="${port}" \
    Language=zh-CN \
    Password=null
fi

exec python gui.py \
  --host 0.0.0.0 \
  --port "${port}" \
  --key "${SRC_WEBUI_PASSWORD}"
