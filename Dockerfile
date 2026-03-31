FROM node:20-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip3 install --break-system-packages --no-cache-dir \
    Flask Flask-Cors Flask-JWT-Extended Flask-Login Flask-Migrate Flask-SQLAlchemy marshmallow

EXPOSE 5000 5173
CMD ["bash"]
