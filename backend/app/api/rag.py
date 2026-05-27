import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.workers.tasks import process_pdf_task
from celery.result import AsyncResult
from app.services.rag_service import ingest_pdf, retrieve_docs
from app.services.llm_service import generate_response
import json
from fastapi.responses import StreamingResponse
from app.services.llm_service import stream_response

from sqlalchemy.orm import Session
from fastapi import Depends

from app.db.session import get_db

from app.models.chat import ChatMessage

router = APIRouter()
APP_DATA_DIR = Path(
    os.getenv(
        "APP_DATA_DIR",
        Path(__file__).resolve().parents[2]
    )
)
UPLOAD_DIR = APP_DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class QueryRequest(BaseModel):

    query: str

    session_id: int | None = None

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    file_path = UPLOAD_DIR / Path(file.filename).name
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    task = process_pdf_task.delay(
        str(file_path)
    )

    return {
        "message": "PDF processing started",
        "task_id": task.id,
        "filename": file.filename
    }

@router.post("/query")
def query_rag(request: QueryRequest):

    docs = retrieve_docs(request.query)

    if len(docs) == 0:

        return {
            "response":
            "No reliable context was found in the uploaded documents.",

            "sources": []
        }

    # Build numbered context pieces so the model can cite sources like [1]
    numbered_contexts = []
    sources = []

    for idx, doc in enumerate(docs, start=1):

        snippet = doc.page_content.strip()

        numbered_contexts.append(f"[SOURCE {idx}]\n{snippet}")

        sources.append({
            "id": idx,
            "content": snippet[:300],
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "N/A"),
            "relevance_score": doc.metadata.get("relevance_score")
        })

    context = "\n\n".join(numbered_contexts)
    context = context[:4000]

    prompt = f"""
    You are OpsPilot AI, a professional AI engineering assistant.

    Answer the user's question using ONLY the retrieved context below. For every factual
    claim you make, append an inline citation in square brackets referencing the
    numbered source (for example: [1], [2]). At the end of your answer include a
    brief "SOURCES:" section that lists the source id, filename and page.

    Rules:
    - Be concise and factual.
    - Use bullet points when helpful.
    - Do NOT hallucinate. If you cannot answer from the provided context, reply exactly:
      "I could not find this information in the uploaded documents."
    - Do NOT provide internal chain-of-thought or hidden reasoning.

    Retrieved Context (numbered):
    {context}

    User Question:
    {request.query}
    """

    response = generate_response(prompt)

    return {
        "response": response,
        "sources_found": len(docs),
        "sources": sources
    }

@router.post("/stream")
async def stream_rag(request: QueryRequest, db: Session = Depends(get_db)):

    if request.session_id:

        user_message = ChatMessage(
            session_id=request.session_id,
            role="user",
            content=request.query
        )

        db.add(user_message)

        db.commit()
    
    docs = retrieve_docs(request.query)

    if not docs:

        return {
            "response": "No matching documentation context found."
        }

    numbered_contexts = []

    for idx, doc in enumerate(docs, start=1):

        numbered_contexts.append(
            f"[SOURCE {idx} | {doc.metadata.get('source', 'Unknown')} | "
            f"Page: {doc.metadata.get('page', 'N/A')}]\n"
            f"{doc.page_content.strip()}"
        )

    context = "\n\n".join(numbered_contexts)

    context = context[:4000]

    prompt = f"""
    You are OpsPilot AI, a professional AI engineering assistant.

    Answer the user's question using ONLY the retrieved context. Cite the source id
    for factual claims using square brackets, for example [1].

    Rules:
    - Be concise and factual
    - Use bullet points when helpful
    - If the answer is not in the context, say:
      "I could not find this information in the uploaded documents."
    - Do not hallucinate information

    Retrieved Context:
    {context}

    User Question:
    {request.query}
    """

    async def generate():

        async for chunk in stream_response(prompt):

            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )


@router.post("/query/verify")
def verify_rag(request: QueryRequest):

    docs = retrieve_docs(request.query)

    if not docs:

        return {
            "response": "No matching documentation context found.",
            "verification": {"verified": False, "issues": []},
            "sources": []
        }

    # Build numbered contexts and sources (same as /query)
    numbered_contexts = []
    sources = []

    for idx, doc in enumerate(docs, start=1):

        snippet = doc.page_content.strip()

        numbered_contexts.append(f"[SOURCE {idx}]\n{snippet}")

        sources.append({
            "id": idx,
            "content": snippet[:300],
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "N/A"),
            "relevance_score": doc.metadata.get("relevance_score")
        })

    context = "\n\n".join(numbered_contexts)
    context = context[:4000]

    answer_prompt = f"""
    You are OpsPilot AI, a professional AI engineering assistant.

    Answer the user's question using ONLY the retrieved context below. For every factual
    claim you make, append an inline citation in square brackets referencing the
    numbered source (for example: [1], [2]). At the end of your answer include a
    brief "SOURCES:" section that lists the source id, filename and page.

    Rules:
    - Be concise and factual.
    - Use bullet points when helpful.
    - Do NOT hallucinate. If you cannot answer from the provided context, reply exactly:
      "I could not find this information in the uploaded documents."
    - Do NOT provide internal chain-of-thought or hidden reasoning.

    Retrieved Context (numbered):
    {context}

    User Question:
    {request.query}
    """

    response = generate_response(answer_prompt)

    # Verification prompt: check each factual claim in the answer and map to sources
    verify_prompt = f"""
    You are a verifier. You will be given an "Answer" and a numbered set of source
    documents. For each distinct factual claim in the Answer, determine whether the
    claim is directly supported by one or more of the provided sources. Output ONLY
    a JSON object with the keys:

    - verified: boolean (true if every factual claim is supported by at least one source)
    - issues: list of objects with keys: claim (string), supporting_sources (list of ids), missing (boolean)

    Use the Retrieved Context below to find supporting evidence. If a claim cannot be
    supported, set "missing": true and "supporting_sources": [].

    Provide only valid JSON.

    Retrieved Context:
    {context}

    Answer:
    {response}
    """

    verify_text = generate_response(verify_prompt)

    verification = None

    try:
        verification = json.loads(verify_text)
    except Exception:
        # If the verifier did not return strict JSON, include raw text
        verification = {"raw": verify_text}

    return {
        "response": response,
        "verification": verification,
        "sources_found": len(docs),
        "sources": sources
    }

@router.get("/task/{task_id}")
def get_task_status(task_id: str):

    task_result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result
    }
