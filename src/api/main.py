from fastapi import FastAPI

from src.api.routes import router

app = FastAPI(title="Enterprise RAG QA API", version="1.0.0")
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
