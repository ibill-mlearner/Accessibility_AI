from __future__ import annotations

from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended.exceptions import JWTExtendedException

class TokenService:
    """JWT and session token lifecycle service.

    # Intent:
    # - Centralize token generation, verification, and rotation rules.
    # - Keep crypto/token details isolated from route handlers and business services.
    """

    def issue_tokens(self, *, user_id: int, claims: dict | None = None) -> dict:
        # Intent (future implementation):
        # 1) Generate access and refresh tokens.
        # 2) Merge base + custom claims.
        # 3) Return transport-ready token response.
        raise NotImplementedError

        return {
            "access_token": "access token",
            "refresh_token": "refresh tokne",
            "token_type": "Bearer"
        }

    def validate_access_token(self, token: str) -> dict:
        # Intent (future implementation):
        # 1) Verify signature and expiry.
        # 2) Validate issuer/audience constraints.
        # 3) Return parsed claims for downstream authorization.
        raise NotImplementedError

        return "decoded_token"