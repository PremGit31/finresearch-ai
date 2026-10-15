# api/models/schemas.py
"""
Pydantic models for the API.
"""
from pydantic import BaseModel, Field
from typing import Optional


class ResearchRequest(BaseModel):
    """Request model for initiating research."""
    query: str = Field(..., description="Research query or question", min_length=5)
    ticker: str = Field(..., description="Stock ticker symbol", min_length=1, max_length=10)


class ResearchResponse(BaseModel):
    """Response model for research results."""
    status: str
    ticker: str
    query: str
    report: str
    citations: list[dict]
    fact_check: dict
    phases_completed: list[str]
    errors: list[str]


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    status: str
    filename: str
    chunks_created: int
    document_id: str


class DocumentStoreInfo(BaseModel):
    """Response model for document store information."""
    name: str
    vectors_count: int
    points_count: int
    status: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    version: str
    services: dict


class StockQueryRequest(BaseModel):
    """Request model for quick stock queries."""
    ticker: str
    include_ratios: bool = False
    include_history: bool = False
    history_period: str = "1mo"