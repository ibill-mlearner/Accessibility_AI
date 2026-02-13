from __future__ import annotations


class AuthService:
    """Authentication workflow coordinator.

    # Intent:
    # - Own high-level auth flow orchestration (login, refresh, logout).
    # - Delegate token signing/verification to TokenService.
    # - Delegate permission checks to PermissionService.
    """

    def authenticate(self, *, identifier: str, password: str) -> dict:
        # Intent (future implementation):
        # 1) Resolve user by identifier.
        # 2) Verify credentials and account state.
        # 3) Return normalized auth payload (user profile + issued tokens).
        raise NotImplementedError

    def refresh_session(self, *, refresh_token: str) -> dict:
        # Intent (future implementation):
        # 1) Validate refresh token.
        # 2) Rotate token pair if required.
        # 3) Return updated auth payload.
        raise NotImplementedError
