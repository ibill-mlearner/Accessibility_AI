FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY AccessBackEnd/requirements.txt /app/AccessBackEnd/requirements.txt
RUN pip install --no-cache-dir -r /app/AccessBackEnd/requirements.txt

COPY package.json /app/package.json
COPY AccessAppFront/package.json AccessAppFront/package-lock.json /app/AccessAppFront/
WORKDIR /app/AccessAppFront
RUN npm install

WORKDIR /app
COPY AccessBackEnd /app/AccessBackEnd
COPY AccessAppFront /app/AccessAppFront
COPY scripts/docker/dev_stack_runner.py /app/scripts/docker/dev_stack_runner.py

EXPOSE 5000 5173

CMD ["python3", "/app/scripts/docker/dev_stack_runner.py"]
