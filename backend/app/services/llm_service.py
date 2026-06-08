import logging
import os

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

llm = ChatGroq(
    model=GROQ_MODEL,
    api_key=GROQ_API_KEY,
    temperature=0,
)

SYSTEM_PROMPT = """
You are OpsPilot AI, a professional AI engineering assistant.

You specialize in:
- AI Engineering
- FastAPI
- LangChain
- LangGraph
- RAG systems
- Vector databases
- Agentic AI
- LLM infrastructure
- Python backend engineering

Rules:
- Give concise and accurate technical responses
- Use markdown formatting
- Use bullet points where useful
- Avoid repetition
- Do not hallucinate fake facts
- If uncertain, clearly say so
"""


def generate_response(message: str, model: str = None) -> str:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message),
    ]
    try:
        active_llm = llm
        if model and model != GROQ_MODEL:
            active_llm = ChatGroq(model=model, api_key=GROQ_API_KEY, temperature=0)
            
        response = active_llm.invoke(messages)
    except Exception as exc:
        logger.error("Groq request failed: %s", exc)
        raise RuntimeError(
            "Groq API is unreachable. Check your GROQ_API_KEY environment variable."
        ) from exc
    return response.content


async def agenerate_response(message: str, config: dict = None, model: str = None) -> str:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message),
    ]
    try:
        active_llm = llm
        if model and model != GROQ_MODEL:
            active_llm = ChatGroq(model=model, api_key=GROQ_API_KEY, temperature=0)
            
        response = await active_llm.ainvoke(messages, config=config)
    except Exception as exc:
        logger.error("Groq async request failed: %s", exc)
        raise RuntimeError(
            "Groq API is unreachable. Check your GROQ_API_KEY environment variable."
        ) from exc
    return response.content


async def stream_response(message: str):
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message),
    ]
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield chunk.content
    except Exception as exc:
        logger.error("Groq stream failed: %s", exc)
        yield "Groq API is unreachable. Check your GROQ_API_KEY environment variable."
