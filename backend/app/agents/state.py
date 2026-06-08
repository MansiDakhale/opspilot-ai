from typing import TypedDict, Literal, Optional


class AgentState(TypedDict):
    """
    Shared state passed through every node in the LangGraph pipeline.

    Fields
    ------
    query           : The raw user question.
    routing_decision: Intent chosen by the Planner.
                      "rag"     – retrieve from ChromaDB then summarise
                      "chat"    – general conversation, no retrieval needed
                      "tools"   – use external tools (web search, ops, …)
    retrieved_docs  : Joined text of retrieved document chunks.
    tool_results    : Output returned by the tool executor (optional).
    final_response  : The assistant's final answer to the user.
    """

    query:            str
    memory_context:   Optional[str]
    model:            Optional[str]
    routing_decision: Optional[Literal["rag", "chat", "tools"]]
    retrieved_docs:   Optional[str]
    tool_results:     Optional[str]
    final_response:   Optional[str]