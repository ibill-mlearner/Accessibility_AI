from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from ..contracts import AIInteractionRepositoryInterface

class AIInteractionRepository(AIInteractionRepositoryInterface):
    """Persistence helpers for AI interaction records."""

    def __init__(self, interaction_model: type):
        self.interaction_model = interaction_model

    def create(
        self,
        session: Session,
        *,
        prompt: str,
        response_text: str,
        chat_id: int | None = None,
        ai_model_id: int | None = None,
        accommodations_id_system_prompts_id: int | None = None,
    ):
        interaction = self.interaction_model(
            prompt=prompt,
            response_text=response_text,
            chat_id=chat_id,
            ai_model_id=ai_model_id,
            accommodations_id_system_prompts_id=accommodations_id_system_prompts_id,
        )
        session.add(interaction)
        session.flush()
        return interaction

    def list_for_chat(self, session: Session, chat_id: int):
        statement = (
            select(self.interaction_model)
            .where(self.interaction_model.chat_id == chat_id)
            .order_by(self.interaction_model.created_at.desc())
        )
        return list(session.scalars(statement))
