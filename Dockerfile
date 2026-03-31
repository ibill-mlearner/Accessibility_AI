FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY AccessBackEnd/requirements.txt /app/AccessBackEnd/requirements.txt
RUN pip install --no-cache-dir -r /app/AccessBackEnd/requirements.txt

COPY AccessAppFront/package*.json /app/AccessAppFront/
RUN npm --prefix /app/AccessAppFront ci

COPY AccessBackEnd /app/AccessBackEnd
COPY AccessAppFront /app/AccessAppFront

EXPOSE 5000 5173

CMD ["sh", "-c", "python3 /app/AccessBackEnd/manage.py & npm --prefix /app/AccessAppFront run dev -- --host 0.0.0.0 --port 5173"]
