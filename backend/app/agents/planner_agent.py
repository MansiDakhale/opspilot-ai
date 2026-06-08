import logging

from app.services.llm_service import generate_response

logger = logging.getLogger(__name__)


_PLANNER_PROMPT = """You are the master routing agent for OpsPilot AI.
Classify the user's query into EXACTLY ONE of these categories:

1. "rag"     - For questions about the user's documents, PDFs, or internal knowledge base.
2. "tools"   - For real-time lookups (web search, docker status, system usage, api requests).
3. "coder"   - ONLY use this if the user explicitly asks you to write code, write a script, or solve a math equation. Do NOT use this for explaining concepts.
4. "report"  - For generating long-form, highly detailed markdown reports or summary documents.
5. "chat"    - For general conversation, greetings, explaining concepts, theory (like architectures), or general AI engineering questions.

Respond with ONLY the exact category name. Nothing else.

Query: {query}"""


def planner_node(state: dict) -> dict:
    """
    Decides the next step in the graph based on the user's query.
    Expected returns:
      - 'rag'     → retrieve documents
      - 'chat'    → standard LLM response
      - 'tools'   → external tool execution (web search, ops checks, …)
      - 'coder'   → python code execution
      - 'report'  → detailed report generation
    """
    query = state["query"]
    memory_context = state.get("memory_context", "")

    try:
        prompt = _PLANNER_PROMPT.format(query=query)
        if memory_context:
            prompt = f"{memory_context}\n\n{prompt}"
        
        decision = generate_response(prompt, model=state.get("model")).strip().lower()

        # Normalise — only accept the valid values
        if decision not in ("rag", "chat", "tools", "coder", "report"):
            logger.warning(
                "Planner returned unexpected value %r for query=%r. "
                "Defaulting to 'rag'.",
                decision, query
            )
            decision = "rag"

    except Exception as exc:
        logger.error("Planner LLM call failed: %s. Defaulting to 'rag'.", exc)
        decision = "rag"

    logger.info("Planner routed query=%r → %s", query, decision)

    return {
        **state,
        "routing_decision": decision,
    }