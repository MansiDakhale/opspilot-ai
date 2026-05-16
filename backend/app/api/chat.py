from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
from app.services.llm_service import llm, generate_response

router = APIRouter()

# Standard Endpoint (Blocking wait)
@router.post("/chat")
def chat(request: ChatRequest):
    response = generate_response(request.message)
    return {"response": response}

# Advanced Streaming Endpoint (Token-by-token)
@router.post("/stream")
async def stream_chat(request: ChatRequest):
    async def generate():
        # Utilizes LangChain's async stream engine
        async for chunk in llm.astream(request.message):
            yield chunk.content

    return StreamingResponse(generate(), media_type="text/plain")