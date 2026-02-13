from __future__ import annotations


class PermissionService:
    """Authorization policy and role mapping service.

    # Intent:
    # - Convert roles/scopes into actionable allow/deny decisions.
    # - Keep authorization policy consistent across routes and domains.
    """

    def can_access(self, *, user_id: int, resource: str, action: str) -> bool:
        # Intent (future implementation):
        # 1) Load user roles and policy bindings.
        # 2) Evaluate role + ownership + scope rules.
        # 3) Return a boolean decision for request guards.
        raise NotImplementedError

    def explain_denial(self, *, user_id: int, resource: str, action: str) -> dict:
        # Intent (future implementation):
        # 1) Re-evaluate policy with debug details.
        # 2) Return structured reason codes/messages for auditing.
        raise NotImplementedError
