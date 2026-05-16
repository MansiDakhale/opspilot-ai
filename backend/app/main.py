from fastapi import FastAPI

from app.api.auth import router as auth_router

from app.db.database import Base, engine

from app.models.user import User

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OpsPilot AI")

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

@app.get("/")
def root():

    return {
        "message": "OpsPilot AI Running"
    }