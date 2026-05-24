# Hugging Face Spaces Docker SDK entrypoint for StarRailCopilot.
# Spaces routes traffic to app_port from README.md; keep this in sync with PORT.
FROM python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HF_HOME=/home/user/.cache/huggingface \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    android-tools-adb \
    build-essential \
    git \
    libavcodec-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavutil-dev \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libsm6 \
    libswresample-dev \
    libswscale-dev \
    libxext6 \
    libxrender1 \
    openssh-client \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /app

COPY --chown=user:user requirements.txt docker-constraints.txt /app/
RUN python -m pip install --upgrade pip setuptools wheel \
    && PIP_CONSTRAINT=/app/docker-constraints.txt python -m pip install -r /app/requirements.txt \
    && python -m pip install "psycopg[binary]>=3.2,<4"

COPY --chown=user:user . /app
RUN mkdir -p /app/config /app/log /app/screenshots /home/user/.cache/huggingface \
    && chown -R user:user /app /home/user

USER user
EXPOSE 7860

CMD ["python", "hf_space_entrypoint.py"]
