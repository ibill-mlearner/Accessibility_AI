from flask import jsonify, session
from flask_login import current_user, login_user, login_required, logout_user

from .routes import BadRequestError, api_v1_bp, db, _read_json_object
from ...models import User
from ...models.identity_defaults import build_transitional_identity_defaults
from ...helpers.auth_helpers import (
    _create_user_session,
    _enforce_roles,
    _normalize_auth_email,
    _resolve_authenticated_session_state,
    _resolved_allowed_actions,
    _unauthorized_auth_envelope,
    revoke_flask_session_lifecycle_record,
)

# ROUTES
@api_v1_bp.post("/auth/login")
def login_auth_user():


    """Authenticate an API-v1 user and establish a login session."""
    payload = _read_json_object()
    email = _normalize_auth_email(payload.get("email"))
    password = payload.get("password") or ""
    if not email or not password:
        raise BadRequestError("email and password are required")

    user = db.session.query(User).filter_by(normalized_email=email).first()
    if user is None or not user.check_password(password):
        return (
            jsonify(
                {
                    "error": {
                        "code": "unauthorized",
                        "message": "invalid credentials",
                        "details": {},
                    }
                }
            ),
            401,
        )
    user.mark_login_success()
    session_record = _create_user_session(user_id=int(user.id))
    login_user(user)
    session["security_stamp"] = user.security_stamp
    session["auth_session_id"] = int(session_record.id)
    # Persists authenticated user id into Flask session, causing session cookie issuance/update.
    db.session.commit()

    return jsonify({"message": "login successful",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "role": user.role}
                    }), 200


@api_v1_bp.get("/auth/session")
@login_required
def get_auth_user_session_status():
    session_record, this_time, auth_err = _resolve_authenticated_session_state()
    if auth_err is not None:
        logout_user()
        session.pop("security_stamp", None)
        session.pop("auth_session_id", None)
        return auth_err

    if session_record is None:
        return _unauthorized_auth_envelope("session not found",
                                           details={"reasons": "unknown"})
    session_record.last_seen_at = this_time
    db.session.commit()

    return (jsonify(
            {
                "ok": True,
                "user": {
                    "id": int(current_user.id),
                    "role": getattr(current_user, "role", None),
                },
                "session": {
                    "id": int(session_record.id),
                    "issued_at": session_record.created_at,
                    "expires_at": session_record.expires_at,
                    "ok_until": session_record.expires_at,
                    "server_time": this_time,
                    "allowed_actions": _resolved_allowed_actions(getattr(current_user, "role", "")),
                },
            }
        ), 200 )

@api_v1_bp.post("/auth/logout")
@login_required
def logout_auth_user():

    revoke_flask_session_lifecycle_record()
    logout_user()
    session.pop("security_stamp", None)
    session.pop("auth_session_id", None)
    return jsonify({"message": "logout successful"}), 200

@api_v1_bp.post("/auth/register")
def register_auth_user():
    """Create and authenticate a user account for API-v1 clients."""
    payload = _read_json_object()
    email = _normalize_auth_email(payload.get("email"))
    password = payload.get("password") or ""
    role = (payload.get("role") or "student").strip().lower()

    if not email or not password:
        raise BadRequestError("email and password are required")

    if db.session.query(User).filter_by(normalized_email=email).first() is not None:
        return (
            jsonify(
                {
                    "error": {
                        "code": "conflict",
                        "message": "email already registered",
                        "details": {},
                    }
                }
            ),
            409,
        )

    user = User(email=email, role=role, **build_transitional_identity_defaults(email))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    user.mark_login_success()
    session_record = _create_user_session(user_id=int(user.id))
    login_user(user)
    session["security_stamp"] = user.security_stamp
    session["auth_session_id"] = int(session_record.id)
    # Persists authenticated user id into Flask session, causing session cookie issuance/update.
    db.session.commit()

    return (
        jsonify(
            {
                "message": "registration successful",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role},
            }
        ),201,
    )

