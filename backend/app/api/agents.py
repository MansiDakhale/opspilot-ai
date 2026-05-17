from fastapi import APIRouter

from pydantic import BaseModel

from app.agents.workflow import app_graph

router = APIRouter()

class AgentRequest(BaseModel):

    query: str

@router.post("/run")

def run_agents(
    request: AgentRequest
):

    result = app_graph.invoke({
        "query": request.query
    })

    return {
        "response": result["final_response"]
    }