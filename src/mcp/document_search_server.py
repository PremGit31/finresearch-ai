# src/mcp/document_search_server.py
"""
MCP Server exposing document search capabilities.
Run with: python -m src.mcp.document_search_server
"""
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DocumentSearch")

# We'll initialize the vector store when running
_vector_store = None


def init_vector_store():
    global _vector_store
    if _vector_store is None:
        try:
            from src.vectorstore.qdrant_store import FinancialVectorStore
            _vector_store = FinancialVectorStore()
        except Exception as e:
            print(f"Warning: Could not initialize vector store: {e}")


@mcp.tool()
def search_financial_documents(query: str, num_results: int = 5) -> str:
    """Search through ingested financial documents for relevant information."""
    init_vector_store()
    if _vector_store is None:
        return json.dumps({"error": "Vector store not available"})

    try:
        results = _vector_store.similarity_search_with_score(query, k=num_results)
        documents = []
        for doc, score in results:
            documents.append({
                "content": doc.page_content[:500],
                "source": doc.metadata.get("filename", "Unknown"),
                "page": doc.metadata.get("page"),
                "section": doc.metadata.get("section"),
                "relevance_score": float(score),
            })
        return json.dumps(documents, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_document_store_info() -> str:
    """Get information about the document store (number of documents, etc.)."""
    init_vector_store()
    if _vector_store is None:
        return json.dumps({"error": "Vector store not available"})

    try:
        info = _vector_store.get_collection_info()
        return json.dumps(info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")