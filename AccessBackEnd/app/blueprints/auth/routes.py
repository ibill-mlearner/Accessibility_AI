from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_user, logout_user

from ...extensions import db
from ...logging_config import DomainEvent
from ...models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "email already registered"}), 409

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    current_app.extensions["event_bus"].publish(DomainEvent("auth.user_registered", {"user_id": user.id, "email": user.email}))

    return jsonify({"id": user.id, "email": user.email, "role": user.role}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401

    login_user(user)
    current_app.extensions["event_bus"].publish(DomainEvent("auth.user_logged_in", {"user_id": user.id, "email": user.email}))

    return jsonify({"message": "login successful", "user": {"id": user.id, "email": user.email}})


@auth_bp.post("/logout")
def logout():
    user_id = current_user.get_id() if current_user.is_authenticated else None
    logout_user()

    current_app.extensions["event_bus"].publish(DomainEvent("auth.user_logged_out", {"user_id": user_id}))

    return jsonify({"message": "logout successful"})
