from langchain_core.runnables import RunnableConfig
from app.services.llm_service import agenerate_response

_CHAT_SYSTEM = """You are OpsPilot AI, a professional AI engineering assistant built into a production-grade agentic platform.

You specialize in:
- AI Engineering and MLOps
- FastAPI, LangChain, LangGraph, RAG systems
- Vector databases and LLM infrastructure
- Python backend engineering
- General software development and deep learning concepts

Rules:
- Be concise, friendly, and accurate
- Use markdown formatting with clear headers and bullet points
- Be self-contained in your answer — the user is already in OpsPilot AI
- If the user wants to ask about a specific uploaded document, tell them to scope the query to their document using the document selector
- Do not hallucinate facts
- Do not tell the user to "ask the RAG system" — you ARE the system"""


async def chat_node(state: dict, config: RunnableConfig) -> dict:
    """
    Handle general conversation queries directly via the LLM
    without any document retrieval.
    """
    query = state["query"]
    memory_context = state.get("memory_context", "")

    prompt = f"{_CHAT_SYSTEM}\n\n{memory_context}\n\nUser: {query}\nAssistant:"

    response = await agenerate_response(prompt, config=config, model=state.get("model"))

    return {
        **state,
        "final_response": response,
    }
