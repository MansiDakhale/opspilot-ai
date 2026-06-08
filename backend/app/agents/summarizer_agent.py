from langchain_core.runnables import RunnableConfig
from app.services.llm_service import agenerate_response


_RAG_PROMPT = """You are an intelligent AI assistant.

Answer the user's question using ONLY the context below.
If the answer is not in the context, reply exactly:
"I could not find this information in the uploaded documents."

Context:
{context}

Question:
{query}"""


_TOOLS_PROMPT = """You are OpsPilot AI, a professional AI engineering assistant.

The following is real-time data retrieved by a tool on the user's behalf.
Summarise it clearly and helpfully. Use markdown formatting and bullet points.

Tool Results:
{tool_results}

User Question:
{query}"""


async def summarizer_node(state: dict, config: RunnableConfig) -> dict:
    """
    Synthesize the final response based on the routing decision:
      - 'rag'   → answer from retrieved document chunks
      - 'tools' → summarize tool output
      - 'chat'  → final_response already set by chat_node; pass through
    """
    routing = state.get("routing_decision", "rag")

    # chat_node already produced the answer — nothing to do
    if routing == "chat":
        return state

    # Tools path: summarise tool output
    if routing == "tools":
        tool_results = state.get("tool_results", "")

        if not tool_results:
            return {**state, "final_response": "The tool returned no results."}

        prompt = _TOOLS_PROMPT.format(
            tool_results=tool_results,
            query=state["query"],
        )
        response = await agenerate_response(prompt, config=config, model=state.get("model"))
        return {**state, "final_response": response}

    # RAG path: answer from document context
    context = state.get("retrieved_docs", "").strip()

    if not context:
        return {
            **state,
            "final_response": "I could not find this information in the uploaded documents.",
        }

    prompt   = _RAG_PROMPT.format(context=context, query=state["query"])
    response = await agenerate_response(prompt, config=config, model=state.get("model"))
    return {**state, "final_response": response}
