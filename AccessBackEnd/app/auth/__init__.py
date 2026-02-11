from .auth_methods import (
    AuthService,
    AuthUser,
    DuplicateIdentityError,
    InMemoryUserStore,
    InvalidCredentialsError,
    PBKDF2PasswordHasher,
    StatelessTokenManager,
    ValidationError,
)

try:
    from .auth_routes import create_auth_blueprint
except ModuleNotFoundError:  # pragma: no cover - optional when Flask isn't installed
    create_auth_blueprint = None

__all__ = [
    "AuthService",
    "AuthUser",
    "DuplicateIdentityError",
    "InMemoryUserStore",
    "InvalidCredentialsError",
    "PBKDF2PasswordHasher",
    "StatelessTokenManager",
    "ValidationError",
    "create_auth_blueprint",
]
