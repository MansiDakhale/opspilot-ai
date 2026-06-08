import logging
import json
import re

from app.services.llm_service import generate_response
from app.db.session import SessionLocal
from app.models.memory import UserMemory

logger = logging.getLogger(__name__)

_MEMORY_PROMPT = """You are a memory extraction agent. 
Analyze the user's message and the assistant's response to extract any persistent, long-term facts about the user.
Look for: preferences, current projects, name, role, tech stack, or specific personal details.

If no long-term facts are present, output an empty array [].
Otherwise, output a JSON array of strings, where each string is a concise fact.

Example Output:
[
  "User is currently building the TSGAN (Tumor-Attentive GAN) thesis project.",
  "User prefers Python and PyTorch.",
  "User's name is Alice."
]

User Message: {user_message}
Assistant Response: {assistant_response}
"""

def extract_and_store_memories(user_id: int, user_message: str, assistant_response: str):
    """
    Runs synchronously (or inside a background task) to extract facts
    and save them to the database.
    """
    if not user_id:
        return

    prompt = _MEMORY_PROMPT.format(
        user_message=user_message,
        assistant_response=assistant_response
    )

    try:
        result_raw = generate_response(prompt)
        # Extract JSON array using regex
        match = re.search(r'\[.*\]', result_raw, re.DOTALL)
        
        if match:
            facts = json.loads(match.group(0))
        else:
            logger.debug("Memory agent found no facts (no JSON array).")
            return

        if not facts or not isinstance(facts, list):
            return

        db = SessionLocal()
        try:
            for fact in facts:
                if isinstance(fact, str) and len(fact) > 5:
                    logger.info(f"Memory Agent extracted fact for user {user_id}: {fact}")
                    db.add(UserMemory(user_id=user_id, fact=fact))
            db.commit()
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Memory extraction failed: {e}")

def get_user_memories(user_id: int, db) -> str:
    """
    Retrieves all stored facts for a user and formats them into a context string.
    """
    if not user_id:
        return ""
        
    memories = db.query(UserMemory).filter(UserMemory.user_id == user_id).order_by(UserMemory.created_at.desc()).limit(20).all()
    
    if not memories:
        return ""
        
    facts = [m.fact for m in memories]
    return "User Background Context:\n" + "\n".join(f"- {f}" for f in facts)
