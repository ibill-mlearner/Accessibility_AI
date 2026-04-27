"""Primary Flask-SQLAlchemy user model.

Table map:
- `users`: account/credential/profile/session-related columns used by Flask-Login auth flows.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from flask_login import UserMixin
from sqlalchemy.orm import validates
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


class User(db.Model, UserMixin):
    """Primary Flask-SQLAlchemy user record used by auth flows.

    Field map:
    - `id`: surrogate primary key for each account.
    - `email`: unique user-supplied login email.
    - `normalized_email`: canonicalized lowercase email used for reliable lookup.
    - `password_hash`: password hash used for credential validation.
    - `role`: role label used for authorization checks.
    - `created_at`: account creation timestamp.
    - `updated_at`: account last-modified timestamp.
    - `last_login_at`: timestamp of the most recent successful login.
    - `is_active`: account-enabled flag for login eligibility.
    - `email_confirmed`: flag tracking email verification completion.
    - `lockout_end`: timestamp after which lockout restrictions are lifted.
    - `access_failed_count`: running count of consecutive failed sign-in attempts.
    - `lockout_enabled`: flag controlling whether lockout policy applies.
    - `security_stamp`: transitional identity-policy marker used for invalidation checks.
    """

    __tablename__ = "users"
    #todo: auth provider and tenant, oid, last remote auth  and token refresh
    # for adding 0365 auth 0-- no time to do this so ignore it
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    normalized_email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # TODO: Replace this with a foreign key/reference to the roles table in a future sprint.
    role = db.Column(db.String(32), nullable=False, default="student")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    lockout_end = db.Column(db.DateTime(timezone=True), nullable=True)
    access_failed_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    lockout_enabled = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    # Transitional placeholder until full identity policy enforcement is implemented.
    security_stamp = db.Column(
        db.String(64), nullable=False, default=lambda: f"transitional-{hashlib.sha256('identity-placeholder'.encode('utf-8')).hexdigest()[:32]}"
    )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @validates("email")
    def _set_normalized_email(self, _key: str, value: str) -> str:
        normalized = self._normalize_email(value)
        self.normalized_email = normalized
        return normalized

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def mark_login_success(self) -> None:
        self.last_login_at = datetime.now(timezone.utc)
        self.access_failed_count = 0

    def __repr__(self) -> str:
        return f"<User {self.email}>"
