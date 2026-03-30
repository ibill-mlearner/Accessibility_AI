@echo off
setlocal

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker is not installed or not on PATH.
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker Desktop / Docker Engine is not running.
  echo Start Docker Desktop and try again.
  exit /b 1
)

echo Starting Accessibility AI with Docker Compose...
docker compose up --build
exit /b %errorlevel%
