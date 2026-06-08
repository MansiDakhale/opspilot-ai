from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User

router = APIRouter()


@router.post("/session")
def create_session(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_optional_user),
):
    """Create a new chat session, linked to the authenticated user if available."""
    session = ChatSession(
        title="New Chat",
        user_id=user.id if user else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id}


@router.get("/sessions")
def get_sessions(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_optional_user),
):
    """Return only the sessions belonging to the current user."""
    query = db.query(ChatSession).order_by(ChatSession.created_at.desc())

    if user:
        query = query.filter(ChatSession.user_id == user.id)

    return query.all()


@router.get("/messages/{session_id}")
def get_messages(
    session_id: int,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_optional_user),
):
    """Return messages for a session, verifying it belongs to the current user."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # If user is authenticated, verify ownership
    if user and session.user_id and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return messages


@router.patch("/session/{session_id}/title")
def update_session_title(
    session_id: int,
    body:       dict,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_optional_user),
):
    """Update a session's title (called after first message to auto-title)."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if user and session.user_id and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    title = body.get("title", "New Chat")
    session.title = title[:60]  # cap at 60 chars
    db.commit()
    return {"ok": True, "title": session.title}


@router.delete("/session/{session_id}")
def delete_session(
    session_id: int,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_optional_user),
):
    """Delete a chat session and all associated messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if user and session.user_id and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    db.delete(session)
    db.commit()
    return {"ok": True, "detail": "Session deleted successfully"}