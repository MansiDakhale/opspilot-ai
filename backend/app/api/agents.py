import json
import logging
import re

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.workflow import app_graph
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.core.deps import get_optional_user
from app.models.user import User
from app.services.rag_service import retrieve_docs, build_context
from app.services.llm_service import generate_response
from app.agents.memory_agent import get_user_memories, extract_and_store_memories

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentRequest(BaseModel):
    query:       str
    session_id:  int | None = None
    document_id: str | None = None   # scope retrieval to a single PDF
    model:       str | None = None   # dynamic model selection


_VERIFY_SYSTEM = """You are a fact-verifier. Given an Answer and numbered source documents,
check each factual claim in the Answer against the sources.

Output ONLY a valid JSON object (no markdown, no code blocks):
{
  "verified": <bool>,
  "issues": [
    {
      "claim": "<claim text>",
      "supporting_sources": [<list of source ids>],
      "missing": <bool>
    }
  ]
}"""


from fastapi.responses import StreamingResponse

@router.post("/stream")
async def stream_agents(
    request: AgentRequest,
    background_tasks: BackgroundTasks,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_optional_user),
):
    query       = request.query
    document_id = request.document_id
    session_id  = request.session_id
    model       = request.model

    # Persist user message upfront
    if session_id:
        db.add(ChatMessage(
            session_id=session_id,
            role="user",
            content=query,
        ))
        db.commit()

    memory_context = get_user_memories(user.id, db) if user else ""

    async def event_generator():
        final_answer = ""
        routing = "rag"

        try:
            inputs = {
                "query":            query,
                "memory_context":   memory_context,
                "model":            model,
                "routing_decision": None,
                "retrieved_docs":   None,
                "tool_results":     None,
                "final_response":   None,
            }

            async for event in app_graph.astream_events(inputs, version="v2"):
                kind = event["event"]

                if kind == "on_chain_end" and event["name"] == "planner":
                    routing = event["data"]["output"].get("routing_decision", "rag")
                    yield f"data: {json.dumps({'type': 'routing', 'value': routing})}\n\n"
                    
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        final_answer += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'value': chunk})}\n\n"

                # If a node sets final_response synchronously (e.g., reporting_node, or summarizer fallback), capture it
                if kind == "on_chain_end" and event["name"] in ("reporting", "summarizer"):
                    output = event["data"]["output"]
                    if "final_response" in output and not final_answer:
                        chunk = output["final_response"]
                        final_answer += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'value': chunk})}\n\n"

            # Post-processing: Sources and Verification for RAG
            sources = []
            verification = None
            if routing == "rag":
                # Wait for retrieval sync (since retrieve_docs is sync)
                # It's fast, but ideally it should be async.
                docs = retrieve_docs(query, document_id=document_id)
                if docs:
                    _, sources = build_context(docs)
                    context_lines = [f"[SOURCE {s['id']} | {s['source']} | Page: {s['page']}]\n{s['content']}" for s in sources]
                    context = "\n\n".join(context_lines)
                    verify_prompt = f"{_VERIFY_SYSTEM}\n\nRetrieved Context:\n{context}\n\nAnswer:\n{final_answer}"
                    try:
                        verify_raw = generate_response(verify_prompt)
                        json_match = re.search(r'\{.*?\}', verify_raw, re.DOTALL)
                        if json_match:
                            verification = json.loads(json_match.group(0))
                        else:
                            raise ValueError("No JSON found in verifier output")
                    except Exception as ve:
                        logger.warning("Verification failed: %s", ve)
                        verification = {"verified": False, "issues": [], "raw": verify_raw}

                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'value': sources})}\n\n"
                if verification:
                    yield f"data: {json.dumps({'type': 'verification', 'value': verification})}\n\n"

            # Persist assistant message
            if session_id and final_answer:
                db.add(ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=final_answer,
                ))
                db.commit()

            if user and final_answer:
                background_tasks.add_task(
                    extract_and_store_memories,
                    user.id,
                    query,
                    final_answer
                )

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            logger.error("Streaming pipeline error: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'value': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")