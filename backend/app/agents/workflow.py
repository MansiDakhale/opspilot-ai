from langgraph.graph import StateGraph

from app.agents.state import AgentState

from app.agents.planner_agent import planner_node

from app.agents.retrieval_agent import retrieval_node

from app.agents.summarizer_agent import summarizer_node

workflow = StateGraph(AgentState)

workflow.add_node(
    "planner",
    planner_node
)

workflow.add_node(
    "retrieval",
    retrieval_node
)

workflow.add_node(
    "summarizer",
    summarizer_node
)

workflow.set_entry_point("planner")

workflow.add_edge(
    "planner",
    "retrieval"
)

workflow.add_edge(
    "retrieval",
    "summarizer"
)

workflow.set_finish_point(
    "summarizer"
)

app_graph = workflow.compile()