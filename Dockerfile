FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir \
    Flask Flask-Cors Flask-JWT-Extended Flask-Login Flask-Migrate Flask-SQLAlchemy marshmallow

EXPOSE 5000 5173
CMD ["bash"]
