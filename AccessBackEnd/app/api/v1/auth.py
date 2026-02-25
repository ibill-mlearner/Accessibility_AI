from flask import jsonify, session, current_app
from flask_login import current_user, login_user, login_required, logout_user

from datetime import UTC, datetime, timedelta
import secrets

from .routes import BadRequestError, api_v1_bp, db, _read_json_object
from ...models import User, UserSession
from ...models.identity_defaults import build_transitional_identity_defaults

# HELPERS

def _normalize_auth_email(value:str | None) -> str:
    return (value or "").strip().lower()

def _resolve_session_timetolive() -> timedelta:
    ttl_value = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")

    # early exit to send back time value from configs
    if isinstance(ttl_value, timedelta):
        return ttl_value

    # if ttl is set as a numeric value
    if isinstance(ttl_value, (int, float)):
        return timedelta(minutes=float(ttl_value))

    # 30 minute timeout default config is already 30 minutes though
    return timedelta(minutes=30)

def _revoke_session_record(session_id: int | None) -> None:
    if not session_id:
        return

    session_record = db.session.get(UserSession, int(session_id))
    if session_record is None:
        return
    now = datetime.now(UTC)
    revoked_at = _as_utc(session_record.revoked_at)
    if revoked_at is not None and revoked_at <= now:
        return

    session_record.revoked_at = now
    db.session.commit()

def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
def _create_user_session(*, user_id: int) -> UserSession:
    now = datetime.now(UTC)
    ttl = _resolve_session_timetolive()
    session_record = UserSession(
        user_id=user_id,
        token_hash=secrets.token_urlsafe(48),
        expires_at=now + ttl,
        last_seen_at=now,
        revoked_at=datetime.max.replace(tzinfo=UTC)
    )
    db.session.add(session_record)
    db.session.flush()
    return session_record


def revoke_flask_session_lifecycle_record() -> None:
    mapped_sessionID = session.get("auth_session_id")
    _revoke_session_record(mapped_sessionID)

def _unauthorized_auth_envelope(message: str, *, details: dict | None = None):
    return (jsonify(
        {
            "error": {
                "code": "unauthorized",
                "message": message,
                "details": details or {}
            }
        }
    ), 401)

#todo: move onto db
def _resolved_allowed_actions(user_role: str) -> list[str]:
    role_val = (user_role or "").strip().lower()
    action_map = {
        "admin": ["users:read", "users:write", "classes:read", "classes:write"],
        "instructor": ["classes:read", "classes:write", "students:read"],
        "student": ["classes:read", "profile:read", "profile:write"]
    }
    return action_map.get(role_val, ["profile:read"])

def _resolve_authenticated_session_state() -> tuple[UserSession | None, datetime, tuple | None]:
    this_time = datetime.now(UTC)

    if not current_user.is_authenticated:
        return None, this_time, _unauthorized_auth_envelope("authentication required")

    persisted_session_id = session.get("auth_session_id")
    if not persisted_session_id:
        return (
            None,
            this_time,
            _unauthorized_auth_envelope(
                "session not found",
                details={"reason": "missing session ID"}
            )
        )

    session_record = db.session.get(UserSession, int(persisted_session_id))
    if session_record is None:
        return (
            None,
            this_time,
            _unauthorized_auth_envelope(
                "session not found",
                details={"reason": "missing session record"}
            )
        )

    if int(session_record.user_id) != int(current_user.id):
        return (
            None,
            this_time,
            _unauthorized_auth_envelope(
                "session user mismatch",
                # this should cover the auth bypass from session storage in front end earlier
                details={"reason": "session user mismatch"}
            )
        )

    revoked_at = _as_utc(session_record.revoked_at)
    if revoked_at is not None and revoked_at <= this_time:
        return (
            None,
            this_time,
            _unauthorized_auth_envelope(
                "session revoked",
                details={"reason": "revoked", "revoked_at": f"{revoked_at}"}
            )
        )

    expires_at = _as_utc(session_record.expires_at)
    if expires_at and expires_at <= this_time:
        session_record.revoked_at = this_time
        db.session.commit()
        return (
            None,
            this_time,
            _unauthorized_auth_envelope(
                "session expired",
                details={"reason": "expired", "expires_at": f"{expires_at}"}
            )
        )

    return session_record, this_time, None


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

def _enforce_roles(*allowed_roles: str):

    allowed_role = {role.strip().lower() for role in allowed_roles if role}

    if not current_user.is_authenticated:
        return jsonify({"error": "authentication required"}), 401

    user_role = (getattr(current_user, "role") or "").strip().lower()
    if allowed_role and user_role not in allowed_roles:
        return (
            jsonify(
                {
                    "error": "forbidden",
                    "required_roles": sorted(allowed_role),
                    "current_role": user_role or None,
                }
            ),
            403,
        )
