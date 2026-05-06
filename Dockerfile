# syntax=docker/dockerfile:1.7

# Base image: python 3.11 slim (lightweight Debian, not a full image)
FROM python:3.11-slim

# Prevent Python from creating .pyc files, container cleanup
ENV PYTHONDONTWRITEBYTECODE=1
# Force Python to output logs immediately for debugging
ENV PYTHONUNBUFFERED=1
# Disable pip version check to speed up installs slightly
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# system dependencies (node, npm, git)
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY AccessBackEnd/requirements.txt /tmp/backend-requirements.txt
RUN pip install -r /tmp/backend-requirements.txt

COPY AccessAppFront/package.json AccessAppFront/package-lock.json /app/AccessAppFront/
WORKDIR /app/AccessAppFront
RUN npm ci

WORKDIR /app
COPY AccessBackEnd /app/AccessBackEnd
COPY AccessAppFront /app/AccessAppFront
COPY scripts/docker/dev_stack_runner.py /app/scripts/docker/dev_stack_runner.py

EXPOSE 5000 5173

CMD ["python3", "/app/scripts/docker/dev_stack_runner.py"]
