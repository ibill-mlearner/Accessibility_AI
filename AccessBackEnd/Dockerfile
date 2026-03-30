# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS backend-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

COPY AccessBackEnd/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY AccessBackEnd /app/AccessBackEnd
COPY scripts /app/scripts

RUN chown -R appuser:appuser /app
USER appuser

WORKDIR /app/AccessBackEnd

EXPOSE 5000

CMD ["python", "manage.py", "--host", "0.0.0.0", "--port", "5000"]


FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS backend-gpu

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common \
        curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

RUN update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1

COPY AccessBackEnd/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY AccessBackEnd /app/AccessBackEnd
COPY scripts /app/scripts

RUN chown -R appuser:appuser /app
USER appuser

WORKDIR /app/AccessBackEnd

EXPOSE 5000

CMD ["python", "manage.py", "--host", "0.0.0.0", "--port", "5000"]
