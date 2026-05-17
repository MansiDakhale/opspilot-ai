import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
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
        
    chunks = ingest_pdf(file_path)
    return {
        "filename": file.filename,
        "chunks_created": chunks
    }

@router.post("/query")
def query_rag(request: QueryRequest):
    docs = retrieve_docs(request.query)
    
    if not docs:
        return {"response": "No matching documentation context found.", "sources_found": 0}
        
    context = "\n\n".join([doc.page_content for doc in docs])
    
    prompt = f"""
    Answer the question based only on the context below. 
    If the context doesn't contain the answer, say "I cannot find the answer in the provided document."

    Context:
    {context}

    Question:
    {request.query}
    """
    
    response = generate_response(prompt)
    return {
        "response": response,
        "sources_found": len(docs)
    }