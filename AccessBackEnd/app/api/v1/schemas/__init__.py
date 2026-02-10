"""Schema contracts for API v1."""

from .auth_schema import LoginRequest, RegisterRequest
from .interaction_schema import AIInteractionRequest, AIInteractionResponse, RetrievalContext
from .resource_schema import ChatRecord, MessageRecord, ResourceEnvelope, ResourceRecord

__all__ = [
    "AIInteractionRequest",
    "AIInteractionResponse",
    "RetrievalContext",
    "LoginRequest",
    "RegisterRequest",
    "ChatRecord",
    "MessageRecord",
    "ResourceEnvelope",
    "ResourceRecord",
]
