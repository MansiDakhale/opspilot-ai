from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from app.db.database import Base

class UserMemory(Base):
    """
    Stores long-term facts extracted from a user's conversations.
    """
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    fact = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
