#!/usr/bin/env python3
"""Standalone end-to-end smoke test runner for Accessibility AI.

Purpose:
- Keep E2E validation outside the application codebase internals.
- Validate a real running stack (frontend + backend) with minimal setup.

What this script checks:
1) Frontend root page responds (Vue app reachable).
2) Backend health endpoint responds.
3) Auth register/login works with session cookies.
4) Core bootstrap collections are reachable (/chats, /classes, /notes, /features).
5) Basic CRUD flow works for class -> chat -> message -> note.
6) AI interaction endpoint responds (for configured provider).

Usage:
  python e2e_smoke/run_e2e_smoke.py \
    --frontend-base http://127.0.0.1:5173 \
    --backend-base http://127.0.0.1:5000

Optional:
  --email e2e.user@example.com
  --password password123
  --role student
  --timeout 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any


class SmokeTestError(RuntimeError):
    pass


@dataclass
class HttpResult:
    status: int
    body: Any


class JsonHttpClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    def request_json(self, method: str, url: str, payload: dict[str, Any] | None = None) -> HttpResult:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url=url, method=method.upper(), data=data, headers=headers)

        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else None
                return HttpResult(status=response.status, body=parsed)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            return HttpResult(status=exc.code, body=parsed)

    def request_text(self, method: str, url: str) -> HttpResult:
        request = urllib.request.Request(url=url, method=method.upper(), headers={"Accept": "text/html,*/*"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return HttpResult(status=response.status, body=raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return HttpResult(status=exc.code, body=raw)


class SmokeRunner:
    def __init__(self, frontend_base: str, backend_base: str, email: str, password: str, role: str, timeout: float):
        self.frontend_base = frontend_base.rstrip("/")
        self.backend_base = backend_base.rstrip("/")
        self.email = email
        self.password = password
        self.role = role
        self.client = JsonHttpClient(timeout=timeout)

    def _assert(self, condition: bool, message: str) -> None:
        if not condition:
            raise SmokeTestError(message)

    def _api(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.backend_base}{path}"

    def _web(self, path: str = "/") -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.frontend_base}{path}"

    def run(self) -> None:
        print("[1/8] Checking frontend is reachable...")
        frontend = self.client.request_text("GET", self._web("/"))
        self._assert(frontend.status == 200, f"Frontend check failed with HTTP {frontend.status}")
        self._assert("<html" in frontend.body.lower(), "Frontend response does not look like HTML")

        print("[2/8] Checking backend health endpoint...")
        health = self.client.request_json("GET", self._api("/api/v1/health"))
        self._assert(health.status == 200, f"Backend health failed with HTTP {health.status}")

        unique_email = self._unique_email(self.email)

        print("[3/8] Registering test user...")
        register = self.client.request_json(
            "POST",
            self._api("/api/v1/auth/register"),
            {"email": unique_email, "password": self.password, "role": self.role},
        )
        self._assert(register.status == 201, f"Register failed with HTTP {register.status} body={register.body}")

        print("[4/8] Logging in test user...")
        login = self.client.request_json(
            "POST",
            self._api("/api/v1/auth/login"),
            {"email": unique_email, "password": self.password},
        )
        self._assert(login.status == 200, f"Login failed with HTTP {login.status} body={login.body}")

        print("[5/8] Verifying bootstrap collections...")
        for resource in ("chats", "classes", "notes", "features"):
            result = self.client.request_json("GET", self._api(f"/api/v1/{resource}"))
            self._assert(result.status == 200, f"GET /{resource} failed with HTTP {result.status}")
            self._assert(isinstance(result.body, list), f"GET /{resource} expected JSON list")

        print("[6/8] Creating class/chat/message/note records...")
        class_resp = self.client.request_json(
            "POST",
            self._api("/api/v1/classes"),
            {
                "name": "E2E Biology",
                "description": "Smoke test class",
                "role": self.role,
                "term": "2026-SPRING",
                "section_code": "E2E01",
                "external_class_key": f"E2E-BIO-{int(time.time())}",
            },
        )
        self._assert(class_resp.status == 201, f"Create class failed HTTP {class_resp.status} body={class_resp.body}")
        class_id = class_resp.body.get("id")
        self._assert(bool(class_id), "Create class response missing id")

        chat_resp = self.client.request_json(
            "POST",
            self._api("/api/v1/chats"),
            {"title": "E2E chat", "class_id": class_id, "model": "gpt-4o-mini"},
        )
        self._assert(chat_resp.status == 201, f"Create chat failed HTTP {chat_resp.status} body={chat_resp.body}")
        chat_id = chat_resp.body.get("id")
        self._assert(bool(chat_id), "Create chat response missing id")

        msg_resp = self.client.request_json(
            "POST",
            self._api("/api/v1/messages"),
            {"chat_id": chat_id, "message_text": "What is ATP?", "help_intent": "summarization"},
        )
        self._assert(msg_resp.status == 201, f"Create message failed HTTP {msg_resp.status} body={msg_resp.body}")

        note_resp = self.client.request_json(
            "POST",
            self._api("/api/v1/notes"),
            {
                "class_id": class_id,
                "chat_id": chat_id,
                "noted_on": "2026-02-10",
                "content": "ATP is cellular energy currency.",
            },
        )
        self._assert(note_resp.status == 201, f"Create note failed HTTP {note_resp.status} body={note_resp.body}")

        print("[7/8] Verifying message listing for created chat...")
        messages = self.client.request_json("GET", self._api(f"/api/v1/chats/{chat_id}/messages"))
        self._assert(messages.status == 200, f"Get chat messages failed HTTP {messages.status} body={messages.body}")
        self._assert(isinstance(messages.body, list), "Expected list from chat messages endpoint")
        self._assert(any(item.get("chat_id") == chat_id for item in messages.body), "Created message not found in chat message list")

        print("[8/8] Exercising AI interaction endpoint...")
        ai_resp = self.client.request_json(
            "POST",
            self._api("/api/v1/ai/interactions"),
            {"prompt": "Explain ATP briefly", "context": {"chat_id": chat_id}},
        )
        self._assert(ai_resp.status in (200, 502), f"AI interaction failed HTTP {ai_resp.status} body={ai_resp.body}")

        print("Smoke E2E completed successfully.")
        if ai_resp.status == 502:
            print("AI provider returned 502 (upstream issue), but endpoint wiring is reachable.")

    @staticmethod
    def _unique_email(seed_email: str) -> str:
        local, _, domain = seed_email.partition("@")
        suffix = int(time.time() * 1000)
        if not domain:
            domain = "example.com"
        return f"{local}+{suffix}@{domain}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run standalone Accessibility AI end-to-end smoke tests")
    parser.add_argument("--frontend-base", default="http://127.0.0.1:5173", help="Frontend base URL")
    parser.add_argument("--backend-base", default="http://127.0.0.1:5000", help="Backend base URL")
    parser.add_argument("--email", default="e2e.user@example.com", help="Base email used for test account")
    parser.add_argument("--password", default="password123", help="Password used for test account")
    parser.add_argument("--role", default="student", choices=["student", "instructor", "admin"], help="Role for test account")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    runner = SmokeRunner(
        frontend_base=args.frontend_base,
        backend_base=args.backend_base,
        email=args.email,
        password=args.password,
        role=args.role,
        timeout=args.timeout,
    )
    try:
        runner.run()
        return 0
    except SmokeTestError as exc:
        print(f"Smoke E2E failed: {exc}")
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error during smoke test: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
