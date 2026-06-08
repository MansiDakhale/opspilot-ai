from langgraph.graph import StateGraph, END

from app.agents.state            import AgentState
from app.agents.planner_agent    import planner_node
from app.agents.retrieval_agent  import retrieval_node
from app.agents.chat_agent       import chat_node
from app.agents.tool_node        import tool_node
from app.agents.coder_agent      import coder_node
from app.agents.reporting_agent  import reporting_node
from app.agents.summarizer_agent import summarizer_node


# ---------------------------------------------------------------------------
# Conditional routing logic
# ---------------------------------------------------------------------------

def route_after_planner(state: AgentState) -> str:
    """
    Called by LangGraph after the planner node runs.
    Returns the name of the NEXT node to execute.
    """
    decision = state.get("routing_decision", "rag")

    if decision == "chat":
        return "chat"
    elif decision == "tools":
        return "tools"
    elif decision == "coder":
        return "coder"
    elif decision == "report":
        return "reporting"
    else:
        return "retrieval"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("planner",   planner_node)
workflow.add_node("retrieval", retrieval_node)
workflow.add_node("chat",      chat_node)
workflow.add_node("tools",     tool_node)
workflow.add_node("coder",     coder_node)
workflow.add_node("reporting", reporting_node)
workflow.add_node("summarizer", summarizer_node)

# Entry point
workflow.set_entry_point("planner")

# Conditional branching: planner → (retrieval | chat | tools | coder | reporting)
workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "retrieval": "retrieval",
        "chat":      "chat",
        "tools":     "tools",
        "coder":     "coder",
        "reporting": "reporting",
    },
)

# All paths converge on the summarizer, except reporting which handles its own response
workflow.add_edge("retrieval", "summarizer")
workflow.add_edge("tools",     "summarizer")
workflow.add_edge("coder",     "summarizer")
workflow.add_edge("chat",      "summarizer")
workflow.add_edge("reporting", END)

# Summarizer is the exit
workflow.add_edge("summarizer", END)

app_graph = workflow.compile()