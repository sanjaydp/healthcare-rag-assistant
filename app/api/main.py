from fastapi import FastAPI
from app.api.routes_query import router as query_router
from app.api.routes_upload import router as upload_router

app = FastAPI(
    title="Healthcare RAG Assistant",
    version="0.1.0",
    description="Backend API for Healthcare RAG Assistant"
)

app.include_router(upload_router, prefix="/upload", tags=["Upload"])
app.include_router(query_router, prefix="/query", tags=["Query"])


@app.get("/")
def root():
    return {
        "message": "Healthcare RAG Assistant API is running"
    }