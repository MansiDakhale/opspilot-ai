import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.workers.tasks import process_pdf_task
from celery.result import AsyncResult
from app.services.rag_service import ingest_pdf, retrieve_docs
from app.services.llm_service import generate_response

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class QueryRequest(BaseModel):
    query: str

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    task = process_pdf_task.delay(
        file_path
    )

    return {
        "message": "PDF processing started",
        "task_id": task.id,
        "filename": file.filename
    }

@router.post("/query")
def query_rag(request: QueryRequest):

    docs = retrieve_docs(request.query)

    if not docs:

        return {
            "response": "No matching documentation context found.",
            "sources_found": 0
        }

    context = "\n\n".join(
        [doc.page_content for doc in docs]
    )

    context = context[:4000]

    prompt = f"""
    You are OpsPilot AI, a professional AI engineering assistant.

    Answer the user's question using ONLY the retrieved context.

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

    response = generate_response(prompt)

    sources = []

    for doc in docs:

        sources.append({

            "content": doc.page_content[:300],

            "source": doc.metadata.get(
                "source",
                "Unknown"
            ),

            "page": doc.metadata.get(
                "page",
                "N/A"
            )
        })

    return {
        "response": response,
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