# api/main.py
"""
FastAPI application — main entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, documents, research

app = FastAPI(
    title="FinResearch AI",
    description="AI-Powered Financial Research & Analysis Agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(documents.router)
app.include_router(research.router)


@app.get("/")
async def root():
    return {
        "name": "FinResearch AI",
        "description": "AI-Powered Financial Research & Analysis Agent",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "upload_document": "POST /documents/upload",
            "search_documents": "POST /documents/search",
            "run_analysis": "POST /research/analyze",
            "quick_quote": "POST /research/quick-quote",
        },
    }