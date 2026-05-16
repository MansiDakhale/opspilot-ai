from fastapi import FastAPI

app = FastAPI(title="OpsPilot AI")

@app.get("/")
def root():
    return {"message": "OpsPilot AI Running"}