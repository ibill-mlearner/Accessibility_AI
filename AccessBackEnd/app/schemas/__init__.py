"""Schema package surface for API contracts.

This package groups two contract styles used in the backend:
- Marshmallow runtime validation schemas (field-level required/optional/nullable rules), and
- TypedDict response/request shape hints used for lightweight static contract documentation.

Handoff note: think of this package as the API payload contract layer—what fields are expected,
which fields may be `None`, and what envelope shapes routes/services should accept/return.
"""

from .auth_schema import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from .interaction_schema import AIInteractionRequest, AIInteractionResponse
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
