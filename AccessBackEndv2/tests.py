"""Prototype full-stack usability test.

Runs AccessBackEndv2 backend and verifies front-end Pinia store can:
1) login,
2) create class/chat/message,
3) request AI interaction.

No edge-case coverage; this is a happy-path prototype check.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "AccessBackEndv2"
FRONTEND_DIR = ROOT / "AccessAppFront"
BASE_URL = "http://127.0.0.1:5055"


def wait_for_backend(timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            res = requests.get(f"{BASE_URL}/api/v1/health", timeout=1.5)
            if res.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.3)
    raise RuntimeError("Backend did not become healthy in time")




def _vite_node_command(frontend_dir: Path) -> list[str]:
    npx_path = shutil.which("npx") or shutil.which("npx.cmd")
    if npx_path:
        return [npx_path, "vite-node"]

    local_bin = frontend_dir / "node_modules" / ".bin" / ("vite-node.cmd" if os.name == "nt" else "vite-node")
    if local_bin.exists():
        return [str(local_bin)]

    local_cli = frontend_dir / "node_modules" / "vite-node" / "vite-node.mjs"
    node_path = shutil.which("node") or shutil.which("node.exe")
    if node_path and local_cli.exists():
        return [node_path, str(local_cli)]

    raise RuntimeError("Could not find vite-node runner. Install Node.js and run npm install in AccessAppFront.")

def run() -> int:
    db_path = BACKEND_DIR / "access_v2.db"
    if db_path.exists():
        db_path.unlink()

    backend = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(BACKEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    try:
        wait_for_backend()

        js_test = textwrap.dedent(
            f"""
            import {{ createPinia, setActivePinia }} from 'pinia'
            import {{ useAppStore }} from './src/stores/appStore.js'
            import api from './src/services/api.js'

            const fail = (m) => {{ console.error(m); process.exit(1) }}

            setActivePinia(createPinia())
            const store = useAppStore()

            const loggedIn = await store.login({{ email: 'demo@access.local', password: 'demo' }})
            if (!loggedIn) fail('store.login returned false')

            // Store login does not persist token header in api client, so set it explicitly.
            const loginResp = await api.post('/api/v1/auth/login', {{ email: 'demo@access.local', password: 'demo' }})
            const token = loginResp?.data?.token
            if (!token) fail('missing token from login')
            api.defaults.headers.common.Authorization = `Bearer ${{token}}`

            await store.createClass({{ name: 'Prototype Class', description: 'MVP class' }})
            const createdClass = store.classes[store.classes.length - 1]
            if (!createdClass?.id) fail('class creation failed')

            const chat = await store.ensureActiveChat({{
              class_id: createdClass.id,
              title: 'Prototype Chat',
              model: 'single-model'
            }})
            if (!chat?.id) fail('chat creation failed')

            const message = await store.createMessage({{
              chat_id: chat.id,
              message_text: 'Hello model, this is a full-stack test.',
              help_intent: 'prototype_validation'
            }})
            if (!message?.id) fail('message creation failed')

            const ai = await store.requestAiInteraction({{
              chat_id: chat.id,
              prompt: 'help me confirm the system works end to end',
              context: {{ source: 'pinia-store-test' }}
            }})
            const text = ai?.response_text || ai?.response || ''
            if (!text) fail('ai response missing')

            console.log('PINIA_FULL_STACK_OK', text)
            """
        )

        with tempfile.NamedTemporaryFile("w", suffix=".mjs", dir=str(FRONTEND_DIR), delete=False) as tf:
            tf.write(js_test)
            js_path = Path(tf.name)

        try:
            env = os.environ.copy()
            env["VITE_API_BASE_URL"] = BASE_URL
            proc = subprocess.run(
                _vite_node_command(FRONTEND_DIR) + [js_path.name],
                cwd=str(FRONTEND_DIR),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                print(proc.stdout)
                print(proc.stderr)
                raise RuntimeError("Pinia full-stack script failed")
            print(proc.stdout.strip())
        finally:
            js_path.unlink(missing_ok=True)

        print("tests.py: PASS")
        return 0
    finally:
        if backend.poll() is None:
            backend.send_signal(signal.SIGTERM)
            try:
                backend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend.kill()


if __name__ == "__main__":
    raise SystemExit(run())
