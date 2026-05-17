from fastapi import FastAPI

from app.api.chat import router as chat_router

from app.api.auth import router as auth_router

from app.api.rag import router as rag_router

from app.api.agents import router as agent_router

from app.db.database import Base, engine

from app.models.user import User

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OpsPilot AI Backend")

# Register Routers
app.include_router(chat_router, prefix="/ai", tags=["AI Chat"])

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

app.include_router(rag_router, prefix="/rag", tags=["RAG Infrastructure"])

app.include_router(
    agent_router,
    prefix="/agents",
    tags=["Agents"]
)

@app.get("/")
def read_root():
    return {"status": "OpsPilot AI Engine is Online"}
