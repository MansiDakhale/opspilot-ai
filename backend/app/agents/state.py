from typing import TypedDict

class AgentState(TypedDict):

    query: str

    retrieved_docs: str

    final_response: str