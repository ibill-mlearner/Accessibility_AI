from __future__ import annotations

import atexit
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_MANAGE = Path('/app/AccessBackEnd/manage.py')
FRONTEND_PACKAGE = Path('/app/AccessAppFront/package.json')
# HTTPS enablement note:
# When TLS is introduced, these should move to `https://...` endpoints that match
# the local TLS terminator/reverse proxy configuration.
HEALTH_URL = 'http://127.0.0.1:5000/api/v1/health'
LOGIN_URL = 'http://127.0.0.1:5000/api/v1/auth/login'


def log(message: str) -> None:
    print(f'[dev_stack_runner] {message}', flush=True)


def require_file(path: Path) -> None:
    if path.exists():
        return
    log(f'ERROR missing required file: {path}')
    for idx, entry in enumerate(sorted(Path('/app').rglob('*'))):
        if idx >= 120:
            break
        if entry.is_file():
            print(entry)
    raise SystemExit(1)


def wait_for_health(timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
                body = response.read().decode('utf-8', errors='replace')
                log(f'health ready: {response.status} {body[:120]}')
                return
        except Exception as exc:
            log(f'waiting for health endpoint: {exc}')
            time.sleep(1)
    raise SystemExit('backend health endpoint did not become ready in time')


def verify_seeded_login() -> None:
    request = urllib.request.Request(
        LOGIN_URL,
        data=json.dumps({'email': 'admin.seed@example.com', 'password': 'Password123!'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode('utf-8'))
    log(f"login smoke passed for: {payload.get('user', {}).get('email')}")


def main() -> int:
    log(f'cwd={Path.cwd()}')
    require_file(BACKEND_MANAGE)
    require_file(FRONTEND_PACKAGE)

    backend = subprocess.Popen(
        ['python3', str(BACKEND_MANAGE), '--init-db', '--host', '0.0.0.0', '--port', '5000'],
    )

    def cleanup() -> None:
        if backend.poll() is None:
            log(f'stopping backend process pid={backend.pid}')
            backend.terminate()

    atexit.register(cleanup)

    wait_for_health()
    verify_seeded_login()

    log('starting frontend dev server')
    frontend = subprocess.run(
        ['npm', '--prefix', '/app/AccessAppFront', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', '5173', '--strictPort'],
        check=False,
    )

    return frontend.returncode


if __name__ == '__main__':
    raise SystemExit(main())
