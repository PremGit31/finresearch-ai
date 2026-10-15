# api/routes/health.py
"""
Health check endpoint.
"""
from fastapi import APIRouter
from api.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health of all services."""
    services = {}

    # Check Qdrant
    try:
        from src.vectorstore.qdrant_store import FinancialVectorStore
        vs = FinancialVectorStore()
        info = vs.get_collection_info()
        services["qdrant"] = "healthy"
        services["documents_indexed"] = info.get("points_count", 0)
    except Exception as e:
        services["qdrant"] = f"unhealthy: {str(e)}"

    # Check Gemini
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from config.settings import GEMINI_API_KEY, GEMINI_MODEL
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY
        )
        services["gemini"] = "healthy"
    except Exception as e:
        services["gemini"] = f"unhealthy: {str(e)}"

    overall = "healthy" if all(
        "healthy" == v for v in services.values() if isinstance(v, str) and v != "healthy"
    ) or all(
        v == "healthy" for v in services.values() if isinstance(v, str)
    ) else "degraded"

    return HealthResponse(
        status=overall,
        version="1.0.0",
        services=services,
    )