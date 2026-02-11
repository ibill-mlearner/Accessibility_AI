from .auth_methods import (
    AuthError,
    AuthService,
    AuthUser,
    InMemoryUserStore,
    SHA256PasswordHasher,
    StatelessTokenIssuer,
)
from .auth_routes import create_auth_blueprint


def create_standalone_auth(*, blueprint_name: str = "auth", url_prefix: str = "/auth"):
    """Build auth service + blueprint with no external infrastructure requirements."""

    auth_service = AuthService(
        user_store=InMemoryUserStore(),
        password_hasher=SHA256PasswordHasher(),
        token_issuer=StatelessTokenIssuer(),
    )
    auth_blueprint = create_auth_blueprint(auth_service, name=blueprint_name, url_prefix=url_prefix)
    return auth_service, auth_blueprint


__all__ = [
    "AuthError",
    "AuthService",
    "AuthUser",
    "InMemoryUserStore",
    "SHA256PasswordHasher",
    "StatelessTokenIssuer",
    "create_auth_blueprint",
    "create_standalone_auth",
]
