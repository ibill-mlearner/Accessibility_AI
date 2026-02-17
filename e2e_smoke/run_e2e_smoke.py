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
import socket
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

    def run(self) -> int:
        results: list[tuple[str, bool, str]] = []
        class_id: Any | None = None
        chat_id: Any | None = None
        unique_email = self._unique_email(self.email)

        def run_step(index: int, title: str, fn) -> None:
            print(f"[{index}/8] {title}...")
            try:
                detail = fn()
                results.append((title, True, detail or "ok"))
                print(f"      PASS: {detail or 'ok'}")
            except Exception as exc:
                results.append((title, False, str(exc)))
                print(f"      FAIL: {exc}")

        def step1() -> str:
            self.frontend_base = self._resolve_frontend_base(self.frontend_base)
            frontend = self.client.request_text("GET", self._web("/"))
            self._assert(frontend.status == 200, f"Frontend check failed with HTTP {frontend.status}")
            self._assert("<html" in frontend.body.lower(), "Frontend response does not look like HTML")
            return f"frontend reachable at {self.frontend_base}"

        def step2() -> str:
            self._preflight_http_target("Backend", self.backend_base)
            health = self.client.request_json("GET", self._api("/api/v1/health"))
            self._assert(health.status == 200, f"Backend health failed with HTTP {health.status}")
            return "backend health returned HTTP 200"

        def step3() -> str:
            register = self.client.request_json(
                "POST",
                self._api("/api/v1/auth/register"),
                {"email": unique_email, "password": self.password, "role": self.role},
            )
            self._assert(register.status == 201, f"Register failed with HTTP {register.status} body={register.body}")
            return f"registered {unique_email}"

        def step4() -> str:
            login = self.client.request_json(
                "POST",
                self._api("/api/v1/auth/login"),
                {"email": unique_email, "password": self.password},
            )
            self._assert(login.status == 200, f"Login failed with HTTP {login.status} body={login.body}")
            return f"logged in as {unique_email}"

        def step5() -> str:
            checked: list[str] = []
            failures: list[str] = []
            for resource in ("chats", "classes", "notes", "features"):
                result = self.client.request_json("GET", self._api(f"/api/v1/{resource}"))
                if result.status != 200:
                    failures.append(f"/{resource}: HTTP {result.status}")
                    continue
                if not isinstance(result.body, list):
                    failures.append(f"/{resource}: expected list")
                    continue
                checked.append(resource)
            self._assert(not failures, "Bootstrap checks failed: " + "; ".join(failures))
            return f"bootstrap resources ok ({', '.join(checked)})"

        def step6() -> str:
            nonlocal class_id, chat_id
            details: list[str] = []

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
            class_id = class_resp.body.get("id") if isinstance(class_resp.body, dict) else None
            self._assert(bool(class_id), "Create class response missing id")
            details.append(f"class={class_id}")

            chat_resp = self.client.request_json(
                "POST",
                self._api("/api/v1/chats"),
                {"title": "E2E chat", "class_id": class_id, "model": "gpt-4o-mini"},
            )
            self._assert(chat_resp.status == 201, f"Create chat failed HTTP {chat_resp.status} body={chat_resp.body}")
            chat_id = chat_resp.body.get("id") if isinstance(chat_resp.body, dict) else None
            self._assert(bool(chat_id), "Create chat response missing id")
            details.append(f"chat={chat_id}")

            msg_resp = self.client.request_json(
                "POST",
                self._api("/api/v1/messages"),
                {"chat_id": chat_id, "message_text": "What is ATP?", "help_intent": "summarization"},
            )
            self._assert(msg_resp.status == 201, f"Create message failed HTTP {msg_resp.status} body={msg_resp.body}")
            details.append("message=created")

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
            details.append("note=created")
            return ", ".join(details)

        def step7() -> str:
            self._assert(bool(chat_id), "Cannot verify chat messages because chat creation did not succeed in step 6")
            messages = self.client.request_json("GET", self._api(f"/api/v1/chats/{chat_id}/messages"))
            self._assert(messages.status == 200, f"Get chat messages failed HTTP {messages.status} body={messages.body}")
            self._assert(isinstance(messages.body, list), "Expected list from chat messages endpoint")
            self._assert(any(item.get("chat_id") == chat_id for item in messages.body), "Created message not found in chat message list")
            return f"verified messages for chat {chat_id}"

        def step8() -> str:
            payload = {"prompt": "Explain ATP briefly", "context": {}}
            if chat_id:
                payload["context"]["chat_id"] = chat_id
            ai_resp = self.client.request_json("POST", self._api("/api/v1/ai/interactions"), payload)
            self._assert(ai_resp.status in (200, 502), f"AI interaction failed HTTP {ai_resp.status} body={ai_resp.body}")
            if ai_resp.status == 502:
                return "endpoint reachable; AI provider returned 502"
            return "AI interaction returned HTTP 200"

        run_step(1, "Checking frontend is reachable", step1)
        run_step(2, "Checking backend health endpoint", step2)
        run_step(3, "Registering test user", step3)
        run_step(4, "Logging in test user", step4)
        run_step(5, "Verifying bootstrap collections", step5)
        run_step(6, "Creating class/chat/message/note records", step6)
        run_step(7, "Verifying message listing for created chat", step7)
        run_step(8, "Exercising AI interaction endpoint", step8)

        print("\nSmoke E2E summary:")
        passed = 0
        for index, (title, ok, detail) in enumerate(results, start=1):
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            print(f"  [{index}/8] {status} - {title}: {detail}")

        print(f"Completed {passed}/8 checks successfully.")
        return 0 if passed == 8 else 1

    @staticmethod
    def _unique_email(seed_email: str) -> str:
        local, _, domain = seed_email.partition("@")
        suffix = int(time.time() * 1000)
        if not domain:
            domain = "example.com"
        return f"{local}+{suffix}@{domain}"

    def _resolve_frontend_base(self, base_url: str) -> str:
        parsed = urllib.parse.urlparse(base_url)
        host = parsed.hostname
        port = parsed.port or (443 if (parsed.scheme or "http") == "https" else 80)
        self._assert(bool(host), f"Frontend base URL is missing a hostname: {base_url}")

        if self._is_tcp_reachable(host, port):
            return base_url

        if host in {"127.0.0.1", "localhost"}:
            sibling_host = "localhost" if host == "127.0.0.1" else "127.0.0.1"
            if self._is_tcp_reachable(sibling_host, port):
                resolved = self._replace_host(base_url, sibling_host)
                print(f"Frontend detected on {resolved} (auto-switched from {base_url}).")
                return resolved

        if host in {"127.0.0.1", "localhost"} and port == 5173:
            discovered = self._discover_listening_local_port(host, [5174, 4173, 3000])
            if discovered is not None:
                resolved = self._replace_port(base_url, discovered)
                print(f"Frontend detected on {resolved} (auto-switched from {base_url}).")
                return resolved

        self._preflight_http_target("Frontend", base_url)
        return base_url

    def _preflight_http_target(self, name: str, base_url: str) -> None:
        parsed = urllib.parse.urlparse(base_url)
        host = parsed.hostname
        port = parsed.port
        scheme = parsed.scheme or "http"

        self._assert(bool(host), f"{name} base URL is missing a hostname: {base_url}")

        if port is None:
            port = 443 if scheme == "https" else 80

        try:
            with socket.create_connection((host, port), timeout=self.client.timeout):
                return
        except OSError as exc:
            hints: list[str] = []
            if name == "Frontend" and host in {"127.0.0.1", "localhost"}:
                sibling_host = "localhost" if host == "127.0.0.1" else "127.0.0.1"
                if self._is_tcp_reachable(sibling_host, port):
                    hints.append(
                        f"Frontend is reachable on {sibling_host}:{port}. "
                        f"Try --frontend-base {self._replace_host(base_url, sibling_host)}"
                    )
            if name == "Frontend" and host in {"127.0.0.1", "localhost"} and port == 5173:
                discovered = self._discover_listening_local_port(host, [5174, 4173, 3000])
                if discovered is not None:
                    hints.append(
                        f"Detected an open frontend-like port at {host}:{discovered}. "
                        f"Try --frontend-base {self._replace_port(base_url, discovered)}"
                    )
                else:
                    hints.append("Start frontend: npm run dev --prefix AccessAppFront")

            if name == "Backend" and host in {"127.0.0.1", "localhost"} and port == 5000:
                hints.append("Start backend: python AccessBackEnd/manage.py --config development")

            hint_text = f" Hints: {' | '.join(hints)}" if hints else ""
            raise SmokeTestError(
                f"{name} is unreachable at {base_url} (host={host}, port={port}, reason={exc}).{hint_text}"
            ) from exc

    def _discover_listening_local_port(self, host: str, ports: list[int]) -> int | None:
        for candidate in ports:
            if self._is_tcp_reachable(host, candidate, timeout=0.4):
                return candidate
        return None

    @staticmethod
    def _replace_host(base_url: str, new_host: str) -> str:
        parsed = urllib.parse.urlparse(base_url)
        host_port = parsed.netloc
        if "@" in host_port:
            auth, _, host_port = host_port.rpartition("@")
        else:
            auth = ""
        if ":" in host_port and not host_port.startswith("["):
            _, _, port_text = host_port.partition(":")
            host_port = f"{new_host}:{port_text}"
        elif host_port.startswith("[") and "]" in host_port:
            after = host_port.split("]", 1)[1]
            host_port = f"{new_host}{after}"
        else:
            host_port = new_host
        if auth:
            host_port = f"{auth}@{host_port}"
        return urllib.parse.urlunparse(parsed._replace(netloc=host_port))

    @staticmethod
    def _replace_port(base_url: str, new_port: int) -> str:
        parsed = urllib.parse.urlparse(base_url)
        host = parsed.hostname or ""
        auth = ""
        if "@" in parsed.netloc:
            auth, _, _ = parsed.netloc.rpartition("@")
        netloc = f"{host}:{new_port}"
        if auth:
            netloc = f"{auth}@{netloc}"
        return urllib.parse.urlunparse(parsed._replace(netloc=netloc))

    def _is_tcp_reachable(self, host: str, port: int, timeout: float | None = None) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout or self.client.timeout):
                return True
        except OSError:
            return False


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
        return runner.run()
    except urllib.error.URLError as exc:
        print(f"Network error during smoke test: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
