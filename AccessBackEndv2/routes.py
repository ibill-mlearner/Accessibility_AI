from __future__ import annotations

from datetime import datetime, timedelta, date
from functools import wraps
import uuid

from flask import g, jsonify, request

from ai import ai_workflow, available_models, default_model
from db import db, ensure_ready, hash_pw, now_iso

SESSION_TTL_HOURS = 24


def parse_iso_datetime(value: str | None) -> str:
    if not value:
        return now_iso()
    datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return str(value)


def parse_iso_date(value: str | None) -> str:
    if not value:
        raise ValueError("date required")
    date.fromisoformat(str(value))
    return str(value)


def json_body() -> dict:
    payload = request.get_json(silent=True)
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("json object body required")
    return payload


def bearer_token() -> str:
    auth = request.headers.get("Authorization", "")
    return auth.replace("Bearer", "", 1).strip() if auth.startswith("Bearer") else ""


def auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        token = bearer_token()
        if not token:
            return jsonify({"error": "invalid credentials"}), 401
        row = db().execute(
            "SELECT user_id, expires_at, revoked FROM sessions WHERE token=?", (token,)
        ).fetchone()
        if not row or row["revoked"]:
            return jsonify({"error": "invalid credentials"}), 401
        if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
            return jsonify({"error": "session expired"}), 401
        g.user_id = int(row["user_id"])
        g.token = token
        return fn(*args, **kwargs)

    return wrapped


def user_or_404(user_id: int):
    return db().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def class_or_404(class_id: int):
    return db().execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()


def chat_or_404(chat_id: int):
    return db().execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()


def can_access_chat(chat_row, user_id: int) -> bool:
    return bool(chat_row and int(chat_row["user_id"]) == int(user_id))


def register_routes(app):
    @app.before_request
    def startup():
        ensure_ready()

    @app.errorhandler(ValueError)
    def handle_value_error(exc):
        return jsonify({"error": str(exc)}), 400

    @app.get("/api/v1/health")
    def health_v1():
        return jsonify({"status": "ok", "ai_provider": default_model(), "available_models": available_models()})


    @app.get("/api/v1/ai/models")
    def list_available_models():
        models = available_models()
        return jsonify({"default_model": models[0], "models": models})

    @app.post("/api/v1/auth/register")
    def auth_register():
        payload = json_body()
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        role = (payload.get("role") or "student").strip().lower()
        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400
        if db().execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            return jsonify({"error": "email already registered"}), 409
        created_at = now_iso()
        db().execute(
            """
            INSERT INTO users (
                email, normalized_email, password_hash, role, created_at, updated_at,
                is_active, email_confirmed, access_failed_count, lockout_enabled, security_stamp
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 0, 0, 1, ?)
            """,
            (email, email, hash_pw(password), role, created_at, created_at, f"transitional-{uuid.uuid4().hex}"),
        )
        user = db().execute("SELECT id, email, role FROM users WHERE email=?", (email,)).fetchone()
        token = str(uuid.uuid4())
        db().execute(
            "INSERT INTO sessions (token, user_id, expires_at, revoked) VALUES (?, ?, ?, 0)",
            (token, user["id"], (datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)).isoformat()),
        )
        db().commit()
        return jsonify({"message": "registration successful", "token": token, "user": dict(user)}), 201

    @app.post("/api/v1/auth/login")
    def auth_login():
        payload = json_body()
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        user = db().execute("SELECT id, email, role, password_hash FROM users WHERE email=?", (email,)).fetchone()
        if not user or user["password_hash"] != hash_pw(password):
            return jsonify({"error": "invalid credentials"}), 401
        token = str(uuid.uuid4())
        db().execute("UPDATE users SET last_login_at=? WHERE id=?", (now_iso(), user["id"]))
        db().execute(
            "INSERT INTO sessions (token, user_id, expires_at, revoked) VALUES (?, ?, ?, 0)",
            (token, user["id"], (datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)).isoformat()),
        )
        db().commit()
        return jsonify({"message": "login successful", "token": token, "user": {"id": user["id"], "email": user["email"], "role": user["role"]}})

    @app.post("/api/v1/auth/logout")
    @auth_required
    def auth_logout():
        db().execute("UPDATE sessions SET revoked=1 WHERE token=?", (g.token,))
        db().commit()
        return jsonify({"token_revoked": True})

    @app.get("/api/v1/auth/me")
    @auth_required
    def auth_me():
        user = user_or_404(g.user_id)
        return jsonify({"user": {"id": user["id"], "email": user["email"], "role": user["role"]}})

    @app.get("/api/v1/chats")
    @auth_required
    def list_chats():
        rows = db().execute("SELECT * FROM chats WHERE user_id=? ORDER BY id DESC", (g.user_id,)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/v1/chats")
    @auth_required
    def create_chat():
        payload = json_body()
        class_id = int(payload.get("class_id") or 1)
        if not class_or_404(class_id):
            return jsonify({"error": "class not found"}), 404
        title = (payload.get("title") or "New Chat").strip()
        model = (payload.get("model") or "single-model").strip()
        started_at = parse_iso_datetime(payload.get("started_at"))
        cur = db().execute(
            "INSERT INTO chats (class_id, user_id, title, model, started_at) VALUES (?, ?, ?, ?, ?)",
            (class_id, g.user_id, title, model, started_at),
        )
        db().commit()
        row = db().execute("SELECT * FROM chats WHERE id=?", (cur.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201

    @app.get("/api/v1/chats/<int:chat_id>")
    @auth_required
    def get_chat(chat_id: int):
        row = chat_or_404(chat_id)
        if not row:
            return jsonify({"error": "chat not found"}), 404
        if not can_access_chat(row, g.user_id):
            return jsonify({"error": "access denied"}), 403
        return jsonify(dict(row))

    @app.route("/api/v1/chats/<int:chat_id>", methods=["PUT", "PATCH"])
    @auth_required
    def update_chat(chat_id: int):
        row = chat_or_404(chat_id)
        if not row:
            return jsonify({"error": "chat not found"}), 404
        if not can_access_chat(row, g.user_id):
            return jsonify({"error": "access denied"}), 403
        payload = json_body()
        db().execute(
            "UPDATE chats SET title=COALESCE(?, title), model=COALESCE(?, model), started_at=COALESCE(?, started_at) WHERE id=?",
            (payload.get("title"), payload.get("model"), payload.get("started_at"), chat_id),
        )
        db().commit()
        return jsonify(dict(chat_or_404(chat_id)))

    @app.delete("/api/v1/chats/<int:chat_id>")
    @auth_required
    def delete_chat(chat_id: int):
        row = chat_or_404(chat_id)
        if not row:
            return jsonify({"error": "chat not found"}), 404
        if not can_access_chat(row, g.user_id):
            return jsonify({"error": "access denied"}), 403
        db().execute("DELETE FROM chats WHERE id=?", (chat_id,))
        db().commit()
        return jsonify(dict(row))

    @app.get("/api/v1/messages")
    @auth_required
    def list_messages():
        rows = db().execute(
            "SELECT m.* FROM messages m JOIN chats c ON c.id=m.chat_id WHERE c.user_id=? ORDER BY m.id ASC",
            (g.user_id,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/v1/messages")
    @auth_required
    def create_message():
        payload = json_body()
        chat_id = payload.get("chat_id")
        if chat_id is None:
            return jsonify({"error": "chat_id is required"}), 400
        chat = chat_or_404(int(chat_id))
        if not chat:
            return jsonify({"error": "chat not found"}), 404
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        text = (payload.get("message_text") or "").strip()
        intent = (payload.get("help_intent") or "").strip()
        if not text or not intent:
            return jsonify({"error": "message_text and help_intent are required"}), 400
        cur = db().execute(
            "INSERT INTO messages (chat_id, message_text, vote, note, help_intent) VALUES (?, ?, ?, ?, ?)",
            (int(chat_id), text, (payload.get("vote") or "good"), (payload.get("note") or "no"), intent),
        )
        db().commit()
        row = db().execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201

    @app.get("/api/v1/messages/<int:message_id>")
    @auth_required
    def get_message(message_id: int):
        row = db().execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        if not row:
            return jsonify({"error": "message not found"}), 404
        chat = chat_or_404(int(row["chat_id"]))
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        return jsonify(dict(row))

    @app.route("/api/v1/messages/<int:message_id>", methods=["PUT", "PATCH"])
    @auth_required
    def update_message(message_id: int):
        row = db().execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        if not row:
            return jsonify({"error": "message not found"}), 404
        chat = chat_or_404(int(row["chat_id"]))
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        payload = json_body()
        db().execute(
            "UPDATE messages SET message_text=COALESCE(?, message_text), vote=COALESCE(?, vote), note=COALESCE(?, note), help_intent=COALESCE(?, help_intent) WHERE id=?",
            (payload.get("message_text"), payload.get("vote"), payload.get("note"), payload.get("help_intent"), message_id),
        )
        db().commit()
        return jsonify(dict(db().execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()))

    @app.delete("/api/v1/messages/<int:message_id>")
    @auth_required
    def delete_message(message_id: int):
        row = db().execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        if not row:
            return jsonify({"error": "message not found"}), 404
        chat = chat_or_404(int(row["chat_id"]))
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        db().execute("DELETE FROM messages WHERE id=?", (message_id,))
        db().commit()
        return jsonify(dict(row))

    @app.get("/api/v1/chats/<int:chat_id>/messages")
    @auth_required
    def list_chat_messages(chat_id: int):
        chat = chat_or_404(chat_id)
        if not chat:
            return jsonify({"error": "chat not found"}), 404
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        rows = db().execute("SELECT * FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/v1/chats/<int:chat_id>/messages")
    @auth_required
    def create_chat_message(chat_id: int):
        payload = json_body()
        payload["chat_id"] = chat_id
        request._cached_json = {False: payload, True: payload}
        return create_message()

    @app.get("/api/v1/classes")
    @auth_required
    def list_classes():
        rows = db().execute("SELECT * FROM classes ORDER BY id ASC").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/v1/classes")
    @auth_required
    def create_class():
        payload = json_body()
        name = (payload.get("name") or "").strip()
        desc = (payload.get("description") or "").strip()
        if not name or not desc:
            return jsonify({"error": "name and description are required"}), 400
        instructor_id = int(payload.get("instructor_id") or g.user_id)
        if not user_or_404(instructor_id):
            return jsonify({"error": "user not found"}), 404
        cur = db().execute(
            "INSERT INTO classes (role, name, description, instructor_id, term, section_code, external_class_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                payload.get("role") or "student",
                name,
                desc,
                instructor_id,
                payload.get("term"),
                payload.get("section_code"),
                payload.get("external_class_key"),
            ),
        )
        db().commit()
        return jsonify(dict(db().execute("SELECT * FROM classes WHERE id=?", (cur.lastrowid,)).fetchone())), 201

    @app.get("/api/v1/classes/<int:class_id>")
    @auth_required
    def get_class(class_id: int):
        row = class_or_404(class_id)
        if not row:
            return jsonify({"error": "class not found"}), 404
        return jsonify(dict(row))

    @app.route("/api/v1/classes/<int:class_id>", methods=["PUT", "PATCH"])
    @auth_required
    def update_class(class_id: int):
        row = class_or_404(class_id)
        if not row:
            return jsonify({"error": "class not found"}), 404
        payload = json_body()
        db().execute(
            "UPDATE classes SET role=COALESCE(?, role), name=COALESCE(?, name), description=COALESCE(?, description), instructor_id=COALESCE(?, instructor_id), term=COALESCE(?, term), section_code=COALESCE(?, section_code), external_class_key=COALESCE(?, external_class_key) WHERE id=?",
            (
                payload.get("role"),
                payload.get("name"),
                payload.get("description"),
                payload.get("instructor_id"),
                payload.get("term"),
                payload.get("section_code"),
                payload.get("external_class_key"),
                class_id,
            ),
        )
        db().commit()
        return jsonify(dict(class_or_404(class_id)))

    @app.delete("/api/v1/classes/<int:class_id>")
    @auth_required
    def delete_class(class_id: int):
        row = class_or_404(class_id)
        if not row:
            return jsonify({"error": "class not found"}), 404
        db().execute("DELETE FROM classes WHERE id=?", (class_id,))
        db().commit()
        return jsonify(dict(row))

    @app.get("/api/v1/features")
    @auth_required
    def list_features():
        rows = db().execute("SELECT * FROM features ORDER BY id ASC").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/v1/features")
    @auth_required
    def create_feature():
        payload = json_body()
        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        if not title or not description:
            return jsonify({"error": "title and description are required"}), 400
        cur = db().execute(
            "INSERT INTO features (title, description, enabled, instructor_id, class_id) VALUES (?, ?, ?, ?, ?)",
            (title, description, 1 if payload.get("enabled") else 0, payload.get("instructor_id"), payload.get("class_id")),
        )
        db().commit()
        return jsonify(dict(db().execute("SELECT * FROM features WHERE id=?", (cur.lastrowid,)).fetchone())), 201

    @app.get("/api/v1/features/<int:feature_id>")
    @auth_required
    def get_feature(feature_id: int):
        row = db().execute("SELECT * FROM features WHERE id=?", (feature_id,)).fetchone()
        if not row:
            return jsonify({"error": "feature not found"}), 404
        return jsonify(dict(row))

    @app.route("/api/v1/features/<int:feature_id>", methods=["PUT", "PATCH"])
    @auth_required
    def update_feature(feature_id: int):
        row = db().execute("SELECT * FROM features WHERE id=?", (feature_id,)).fetchone()
        if not row:
            return jsonify({"error": "feature not found"}), 404
        payload = json_body()
        db().execute(
            "UPDATE features SET title=COALESCE(?, title), description=COALESCE(?, description), enabled=COALESCE(?, enabled), instructor_id=COALESCE(?, instructor_id), class_id=COALESCE(?, class_id) WHERE id=?",
            (payload.get("title"), payload.get("description"), payload.get("enabled"), payload.get("instructor_id"), payload.get("class_id"), feature_id),
        )
        db().commit()
        return jsonify(dict(db().execute("SELECT * FROM features WHERE id=?", (feature_id,)).fetchone()))

    @app.delete("/api/v1/features/<int:feature_id>")
    @auth_required
    def delete_feature(feature_id: int):
        row = db().execute("SELECT * FROM features WHERE id=?", (feature_id,)).fetchone()
        if not row:
            return jsonify({"error": "feature not found"}), 404
        db().execute("DELETE FROM features WHERE id=?", (feature_id,))
        db().commit()
        return jsonify(dict(row))

    @app.get("/api/v1/notes")
    @auth_required
    def list_notes():
        rows = db().execute(
            "SELECT n.* FROM notes n JOIN chats c ON c.id=n.chat_id WHERE c.user_id=? ORDER BY n.id ASC",
            (g.user_id,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/v1/notes")
    @auth_required
    def create_note():
        payload = json_body()
        class_id = payload.get("class_id")
        chat_id = payload.get("chat_id")
        content = (payload.get("content") or "").strip()
        if class_id is None or chat_id is None:
            return jsonify({"error": "class_id and chat_id are required"}), 400
        if not class_or_404(int(class_id)):
            return jsonify({"error": "class not found"}), 404
        chat = chat_or_404(int(chat_id))
        if not chat:
            return jsonify({"error": "chat not found"}), 404
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        if not content:
            return jsonify({"error": "content is required"}), 400
        noted_on = parse_iso_date(payload.get("noted_on"))
        cur = db().execute(
            "INSERT INTO notes (class_id, chat_id, noted_on, content) VALUES (?, ?, ?, ?)",
            (int(class_id), int(chat_id), noted_on, content),
        )
        db().commit()
        return jsonify(dict(db().execute("SELECT * FROM notes WHERE id=?", (cur.lastrowid,)).fetchone())), 201

    @app.get("/api/v1/notes/<int:note_id>")
    @auth_required
    def get_note(note_id: int):
        row = db().execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if not row:
            return jsonify({"error": "note not found"}), 404
        chat = chat_or_404(int(row["chat_id"]))
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        return jsonify(dict(row))

    @app.route("/api/v1/notes/<int:note_id>", methods=["PUT", "PATCH"])
    @auth_required
    def update_note(note_id: int):
        row = db().execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if not row:
            return jsonify({"error": "note not found"}), 404
        chat = chat_or_404(int(row["chat_id"]))
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        payload = json_body()
        db().execute(
            "UPDATE notes SET class_id=COALESCE(?, class_id), chat_id=COALESCE(?, chat_id), noted_on=COALESCE(?, noted_on), content=COALESCE(?, content) WHERE id=?",
            (payload.get("class_id"), payload.get("chat_id"), payload.get("noted_on"), payload.get("content"), note_id),
        )
        db().commit()
        return jsonify(dict(db().execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()))

    @app.delete("/api/v1/notes/<int:note_id>")
    @auth_required
    def delete_note(note_id: int):
        row = db().execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if not row:
            return jsonify({"error": "note not found"}), 404
        chat = chat_or_404(int(row["chat_id"]))
        if not can_access_chat(chat, g.user_id):
            return jsonify({"error": "access denied"}), 403
        db().execute("DELETE FROM notes WHERE id=?", (note_id,))
        db().commit()
        return jsonify(dict(row))

    @app.post("/api/v1/ai/interactions")
    @auth_required
    def create_ai_interaction():
        payload = json_body()
        prompt = payload.get("prompt") or ""
        result = ai_workflow(prompt=prompt, context=payload.get("context"), initiated_by=str(g.user_id))
        db().execute(
            "INSERT INTO ai_interactions (prompt, response_text, provider, chat_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (prompt, result["response_text"], result.get("provider", default_model()), payload.get("chat_id"), now_iso()),
        )
        db().commit()
        return jsonify(result), 200

    @app.get("/api/health")
    def health_alias():
        return health_v1()

    @app.post("/api/login")
    def login_alias():
        return auth_login()

    @app.get("/api/session")
    @auth_required
    def session_alias():
        row = db().execute("SELECT expires_at FROM sessions WHERE token=?", (g.token,)).fetchone()
        return jsonify({"user_id": g.user_id, "expires_at": row["expires_at"]})

    @app.get("/api/entity/me")
    @auth_required
    def entity_alias():
        user = user_or_404(g.user_id)
        return jsonify({"entity_id": user["id"], "display_name": user["email"], "role": user["role"]})

    @app.post("/api/chat")
    @auth_required
    def chat_alias():
        payload = json_body()
        text = (payload.get("message") or "").strip()
        if not text:
            return jsonify({"error": "message required"}), 400
        existing_chat = db().execute("SELECT id FROM chats WHERE user_id=? ORDER BY id DESC LIMIT 1", (g.user_id,)).fetchone()
        if not existing_chat:
            cur = db().execute(
                "INSERT INTO chats (class_id, user_id, title, model, started_at) VALUES (1, ?, 'Quick Chat', 'single-model', ?)",
                (g.user_id, now_iso()),
            )
            chat_id = cur.lastrowid
        else:
            chat_id = existing_chat["id"]
        result = ai_workflow(text, initiated_by=str(g.user_id))
        mcur = db().execute(
            "INSERT INTO messages (chat_id, message_text, vote, note, help_intent) VALUES (?, ?, 'good', 'no', 'chat')",
            (chat_id, text),
        )
        db().execute(
            "INSERT INTO ai_interactions (prompt, response_text, provider, chat_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (text, result["response_text"], result["provider"], chat_id, now_iso()),
        )
        db().commit()
        return jsonify({"chat_id": chat_id, "message_id": mcur.lastrowid, "response": result["response_text"]})

    @app.get("/api/chat/history")
    @auth_required
    def history_alias():
        rows = db().execute(
            "SELECT m.id, m.chat_id, m.message_text, m.help_intent FROM messages m JOIN chats c ON c.id=m.chat_id WHERE c.user_id=? ORDER BY m.id DESC LIMIT 50",
            (g.user_id,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])
