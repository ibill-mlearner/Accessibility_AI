from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import validates
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .identity_defaults import build_transitional_security_stamp


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    normalized_email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
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
        db.String(64), nullable=False, default=lambda: build_transitional_security_stamp(None)
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
