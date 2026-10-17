"""Conversation memory: Save and retrieve chat messages."""

import uuid
from src.database import SessionLocal
from src.models.student_models import ConversationMessageModel


def save_message(
    student_id: int, role: str, content: str, conversation_id: str = None
) -> str:
    with SessionLocal() as db:
        msg = ConversationMessageModel(
            student_id=student_id,
            conversation_id=conversation_id or str(uuid.uuid4()),
            role=role,
            content=content,
        )
        db.add(msg)
        db.commit()
        return msg.conversation_id


def get_recent_messages(student_id: int, limit: int = 10) -> list[dict]:
    with SessionLocal() as db:
        messages = (
            db.query(ConversationMessageModel)
            .filter_by(student_id=student_id)
            .order_by(ConversationMessageModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(messages)
        ]
