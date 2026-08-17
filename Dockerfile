ARG BASE_IMAGE=bgzerol/starrailcopilot:slim@sha256:fb3cc1d3d180f381c81e5a05683782fbbf02590613abf5f59c65b2f12762745f
FROM ${BASE_IMAGE}

USER root
WORKDIR /app

# 基础镜像提供 Python 3.10、ADB、Git 与图像处理运行库；应用源码始终使用本 fork 的当前版本。
RUN find /app -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
COPY . /app

RUN python -m pip install --no-cache-dir -r requirements-in.txt \
    && command -v python \
    && command -v git \
    && command -v adb \
    && install -m 0755 deploy/docker-entrypoint.sh /usr/local/bin/starrail-entrypoint

ENV PORT=22367 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

EXPOSE 22367

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:22367/', timeout=4)" || exit 1

ENTRYPOINT ["/usr/local/bin/starrail-entrypoint"]
CMD []
