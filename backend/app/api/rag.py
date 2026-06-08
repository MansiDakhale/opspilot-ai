import os
import json
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.workers.tasks import process_pdf_task
from app.workers.celery_app import celery
from app.services.rag_service import ingest_pdf, retrieve_docs, build_context
from app.services.llm_service import generate_response, stream_response
from app.db.session import get_db
from app.models.chat import ChatMessage

router = APIRouter()

# ---------------------------------------------------------------------------
# Upload directory
# ---------------------------------------------------------------------------

APP_DATA_DIR = Path(
    os.getenv("APP_DATA_DIR", Path(__file__).resolve().parents[2])
)
UPLOAD_DIR = APP_DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query:       str
    session_id:  int | None = None
    # Optional: scope retrieval to a single document (stem of filename, e.g. "my_report")
    document_id: str | None = None


# ---------------------------------------------------------------------------
# Shared prompt builders
# ---------------------------------------------------------------------------

_ANSWER_SYSTEM = """You are OpsPilot AI, a professional AI engineering assistant.

Answer the user's question using ONLY the retrieved context below.
For every factual claim, append an inline citation like [1] or [2].
End your answer with a brief "SOURCES:" section listing source id, filename, and page.

Rules:
- Be concise and factual.
- Use bullet points where helpful.
- If the answer is NOT in the context, reply exactly:
  "I could not find this information in the uploaded documents."
- Do NOT hallucinate or guess."""


def _build_answer_prompt(context: str, query: str) -> str:
    return (
        f"{_ANSWER_SYSTEM}\n\n"
        f"Retrieved Context (numbered):\n{context}\n\n"
        f"User Question:\n{query}"
    )


_VERIFY_SYSTEM = """You are a fact-verifier. Given an Answer and numbered source documents,
check each factual claim in the Answer against the sources.

Output ONLY a valid JSON object with:
{
  "verified": <bool>,
  "issues": [
    {
      "claim": "<claim text>",
      "supporting_sources": [<list of source ids>],
      "missing": <bool>
    }
  ]
}
No extra text outside the JSON."""


def _build_verify_prompt(context: str, answer: str) -> str:
    return (
        f"{_VERIFY_SYSTEM}\n\n"
        f"Retrieved Context:\n{context}\n\n"
        f"Answer:\n{answer}"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF; triggers async Celery ingestion task."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = UPLOAD_DIR / Path(file.filename).name

    with open(file_path, "wb") as f:
        f.write(await file.read())

    task = process_pdf_task.delay(str(file_path))

    return {
        "message":     "PDF processing started",
        "task_id":     task.id,
        "filename":    file.filename,
        "document_id": Path(file.filename).stem,   # return so frontend can scope queries
    }


@router.post("/query")
def query_rag(request: QueryRequest):
    """Retrieve context → generate a cited answer (blocking)."""
    docs = retrieve_docs(request.query, document_id=request.document_id)

    if not docs:
        return {
            "response":      "No reliable context was found in the uploaded documents.",
            "sources_found": 0,
            "sources":       [],
        }

    context, sources = build_context(docs)
    prompt           = _build_answer_prompt(context, request.query)

    try:
        response = generate_response(prompt)
    except RuntimeError as exc:
        return {"response": str(exc), "sources_found": len(docs), "sources": sources}

    return {
        "response":      response,
        "sources_found": len(docs),
        "sources":       sources,
    }


@router.post("/stream")
async def stream_rag(request: QueryRequest, db: Session = Depends(get_db)):
    """Retrieve context → stream the answer token-by-token."""
    # Persist user message
    if request.session_id:
        db.add(ChatMessage(
            session_id=request.session_id,
            role="user",
            content=request.query,
        ))
        db.commit()

    docs = retrieve_docs(request.query, document_id=request.document_id)

    if not docs:
        async def _no_context():
            yield "No matching documentation context found."
        return StreamingResponse(_no_context(), media_type="text/plain")

    context, _ = build_context(docs)
    prompt      = _build_answer_prompt(context, request.query)

    # Collect full response so we can persist it after streaming
    full_response_parts: list[str] = []

    async def generate():
        async for chunk in stream_response(prompt):
            full_response_parts.append(chunk)
            yield chunk

        # Persist AI response after stream completes
        if request.session_id:
            db.add(ChatMessage(
                session_id=request.session_id,
                role="assistant",
                content="".join(full_response_parts),
            ))
            db.commit()

    return StreamingResponse(generate(), media_type="text/plain")


@router.post("/query/verify")
def verify_rag(request: QueryRequest):
    """Retrieve → answer → verify each claim against sources."""
    docs = retrieve_docs(request.query, document_id=request.document_id)

    if not docs:
        return {
            "response":      "No matching documentation context found.",
            "verification":  {"verified": False, "issues": []},
            "sources_found": 0,
            "sources":       [],
        }

    context, sources = build_context(docs)

    # Step 1: Generate answer
    try:
        answer = generate_response(_build_answer_prompt(context, request.query))
    except RuntimeError as exc:
        return {
            "response": str(exc),
            "verification": {
                "verified": False,
                "issues": [{"claim": str(exc), "supporting_sources": [], "missing": True}],
            },
            "sources_found": len(docs),
            "sources": sources,
        }

    # Step 2: Verify claims
    try:
        verify_raw = generate_response(_build_verify_prompt(context, answer))
    except RuntimeError as exc:
        verify_raw = json.dumps({
            "verified": False,
            "issues": [{"claim": str(exc), "supporting_sources": [], "missing": True}],
        })

    try:
        # Strip markdown formatting if present
        clean_json = verify_raw.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()
        
        verification = json.loads(clean_json)
    except Exception:
        verification = {"raw": verify_raw}

    return {
        "response":      answer,
        "verification":  verification,
        "sources_found": len(docs),
        "sources":       sources,
    }


@router.get("/task/{task_id}")
def get_task_status(task_id: str):
    """Poll a Celery ingestion task."""
    task_result = celery.AsyncResult(task_id)
    result      = task_result.result

    if isinstance(result, Exception):
        result = {"error": str(result)}

    return {
        "task_id": task_id,
        "status":  task_result.status,
        "result":  result,
    }
