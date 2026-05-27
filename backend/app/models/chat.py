from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship

from datetime import datetime

from app.db.database import Base


class ChatSession(Base):

    __tablename__ = "chat_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete"
    )


class ChatMessage(Base):

    __tablename__ = "chat_messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id")
    )

    role = Column(String)

    content = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    session = relationship(
        "ChatSession",
        back_populates="messages"
    )