# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json /app/
COPY AccessBackEnd/requirements.txt /tmp/backend-requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY AccessAppFront/package.json AccessAppFront/package-lock.json /app/AccessAppFront/
WORKDIR /app/AccessAppFront
RUN --mount=type=cache,target=/root/.npm \
    npm ci

WORKDIR /app
COPY AccessBackEnd /app/AccessBackEnd
COPY AccessAppFront /app/AccessAppFront
COPY scripts/docker/dev_stack_runner.py /app/scripts/docker/dev_stack_runner.py

EXPOSE 5000 5173

CMD ["python3", "/app/scripts/docker/dev_stack_runner.py"]
