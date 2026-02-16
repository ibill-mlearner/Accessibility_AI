"""Schema contracts for API v1."""

from .auth_schema import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from .interaction_schema import AIInteractionRequest, AIInteractionResponse, RetrievalContext
from .resource_schema import (
    ChatCreateRequest,
    ChatListResponse,
    ChatRecord,
    MessageCreateRequest,
    MessageListResponse,
    MessageRecord,
    PlaceholderTodoResponse,
)

__all__ = [
    "AIInteractionRequest",
    "AIInteractionResponse",
    "RetrievalContext",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "ChatCreateRequest",
    "ChatListResponse",
    "ChatRecord",
    "MessageCreateRequest",
    "MessageListResponse",
    "MessageRecord",
    "PlaceholderTodoResponse",
]
