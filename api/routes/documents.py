# api/routes/documents.py
"""
Document management endpoints.
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from config.settings import RAW_DIR
from src.ingestion.document_loader import FinancialDocumentLoader
from src.ingestion.chunker import FinancialDocumentChunker
from src.vectorstore.qdrant_store import FinancialVectorStore
from src.tools.document_search import set_vector_store
from api.models.schemas import DocumentUploadResponse, DocumentStoreInfo

router = APIRouter(prefix="/documents", tags=["documents"])

# Module-level instances
_loader = FinancialDocumentLoader()
_chunker = FinancialDocumentChunker()
_vector_store = None


def get_vector_store() -> FinancialVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = FinancialVectorStore()
        set_vector_store(_vector_store)
    return _vector_store


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    company: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
):
    """Upload and ingest a financial document."""
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in _loader.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {_loader.SUPPORTED_EXTENSIONS}",
        )

    # Save file
    save_path = RAW_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Build metadata
    metadata = {}
    if company:
        metadata["company"] = company
    if document_type:
        metadata["document_type"] = document_type
    if year:
        metadata["year"] = year

    # Load and chunk
    try:
        documents = _loader.load(save_path, metadata)
        chunks = _chunker.chunk_documents(documents)

        # Index in vector store
        vs = get_vector_store()
        ids = vs.add_documents(chunks)

        return DocumentUploadResponse(
            status="success",
            filename=file.filename,
            chunks_created=len(chunks),
            document_id=ids[0] if ids else "unknown",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/info", response_model=DocumentStoreInfo)
async def get_store_info():
    """Get information about the document store."""
    try:
        vs = get_vector_store()
        info = vs.get_collection_info()
        return DocumentStoreInfo(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents_endpoint(query: str, num_results: int = 5):
    """Search through ingested documents."""
    try:
        vs = get_vector_store()
        results = vs.similarity_search_with_score(query, k=num_results)
        return {
            "query": query,
            "results": [
                {
                    "content": doc.page_content[:500],
                    "metadata": doc.metadata,
                    "score": float(score),
                }
                for doc, score in results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))