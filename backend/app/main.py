import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

from app.api.chat import router as chat_router

from app.api.auth import router as auth_router

from app.api.rag import router as rag_router

from app.api.agents import router as agent_router

from app.db.database import Base, engine

from app.models.user import User

from fastapi.middleware.cors import CORSMiddleware

from app.models.chat import ChatSession
from app.models.chat import ChatMessage
from app.models.memory import UserMemory

from app.api.chat_history import router as history_router

Base.metadata.create_all(bind=engine)

# Ensure the reports directory exists
os.makedirs("uploads/reports", exist_ok=True)

# Configure basic logging once at application startup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

app = FastAPI(title="OpsPilot AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

app.include_router(
    history_router,
    prefix="/history",
    tags=["History"]
)

# Serve the reports directory so the frontend can download them
app.mount("/reports", StaticFiles(directory="uploads/reports"), name="reports")

@app.get("/")
def read_root():
    return {"status": "OpsPilot AI Engine is Online"}
