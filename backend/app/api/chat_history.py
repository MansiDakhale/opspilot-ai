from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.models.chat import (
    ChatSession,
    ChatMessage
)

router = APIRouter()


@router.post("/session")
def create_session(
    db: Session = Depends(get_db)
):

    session = ChatSession(
        title="New Chat"
    )

    db.add(session)

    db.commit()

    db.refresh(session)

    return {
        "session_id": session.id
    }


@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db)
):

    sessions = db.query(
        ChatSession
    ).order_by(
        ChatSession.created_at.desc()
    ).all()

    return sessions


@router.get("/messages/{session_id}")
def get_messages(
    session_id: int,
    db: Session = Depends(get_db)
):

    messages = db.query(
        ChatMessage
    ).filter(
        ChatMessage.session_id == session_id
    ).all()

    return messages