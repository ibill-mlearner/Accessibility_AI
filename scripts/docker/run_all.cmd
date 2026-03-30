@echo off
setlocal

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker is not installed or not on PATH.
  exit /b 1
)

set PROFILE=dev
set BACKEND_SERVICE=backend
set FRONTEND_SERVICE=frontend

echo Checking NVIDIA GPU container runtime...
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi >nul 2>&1
if not errorlevel 1 (
  set PROFILE=gpu
  set BACKEND_SERVICE=backend-gpu
  echo NVIDIA runtime detected. Using GPU backend profile.
) else (
  echo NVIDIA runtime not detected. Falling back to CPU backend profile.
)

echo Initializing database...
docker compose --profile %PROFILE% run --rm %BACKEND_SERVICE% python manage.py --init-db
if errorlevel 1 (
  echo [ERROR] Database initialization failed.
  exit /b 1
)

echo Starting application stack...
docker compose --profile %PROFILE% up --build %BACKEND_SERVICE% %FRONTEND_SERVICE%
exit /b %errorlevel%
