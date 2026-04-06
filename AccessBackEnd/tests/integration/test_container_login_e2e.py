import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(f"[container-e2e] $ {' '.join(cmd)}")
    if result.stdout:
        print(f"[container-e2e][stdout]\n{result.stdout}")
    if result.stderr:
        print(f"[container-e2e][stderr]\n{result.stderr}")
    if check and result.returncode != 0:
        raise AssertionError(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result


def _wait_for_login_ready(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            request = urllib.request.Request(
                "http://127.0.0.1:5000/api/v1/auth/login",
                data=json.dumps({"email": "x", "password": "y"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                # Login endpoint should not be 2xx for fake creds, but if it is,
                # backend is definitely reachable.
                print(f"[container-e2e] login endpoint probe status={response.status}")
                return
        except urllib.error.HTTPError as exc:
            # 401 from invalid credentials means backend is up.
            if exc.code == 401:
                print("[container-e2e] login endpoint probe reached backend (401 as expected)")
                return
            print(f"[container-e2e] probe HTTP error: {exc.code}")
        except Exception as exc:
            print(f"[container-e2e] waiting for backend: {exc}")
        time.sleep(2)
    raise AssertionError("containerized backend did not become ready in time")


@pytest.mark.integration
def test_containerized_seeded_login_round_trip():
    if shutil.which("docker") is None:
        pytest.skip("docker CLI is required for containerized integration test")

    # Always cleanup first to avoid stale/orphan state polluting this run.
    _run(["docker", "compose", "down", "--remove-orphans", "--volumes"], check=False)

    try:
        _run(["docker", "compose", "up", "-d", "--build"])
        _wait_for_login_ready(timeout_seconds=180)

        request = urllib.request.Request(
            "http://127.0.0.1:5000/api/v1/auth/login",
            data=json.dumps(
                {
                    "email": "admin.seed@example.com",
                    "password": "Password123!",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))

        print(f"[container-e2e] login response body={body}")
        assert body["message"] == "login successful"
        assert body["user"]["email"] == "admin.seed@example.com"
    finally:
        _run(["docker", "compose", "logs", "--no-color"], check=False)
        _run(["docker", "compose", "down", "--remove-orphans", "--volumes"], check=False)
