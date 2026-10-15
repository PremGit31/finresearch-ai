# src/tools/document_search.py
"""
RAG document search tool — searches the vector store for relevant passages.
"""
from langchain_core.tools import tool


# We need a module-level reference that gets set when the app initializes
_vector_store = None


def set_vector_store(vs):
    """Set the vector store instance for the search tool."""
    global _vector_store
    _vector_store = vs


@tool
def search_documents(query: str, num_results: int = 5) -> str:
    """
    Search through ingested financial documents (annual reports, earnings transcripts,
    SEC filings) for relevant information.

    Args:
        query: Search query describing what information you need
        num_results: Number of relevant passages to return (default 5)

    Returns:
        Relevant passages from financial documents with source citations.
    """
    if _vector_store is None:
        return "Error: Document store not initialized. No documents have been ingested yet."

    try:
        results = _vector_store.similarity_search_with_score(query, k=num_results)

        if not results:
            return f"No relevant documents found for: '{query}'"

        output = f"**Document Search Results for:** '{query}'\n\n"
        for i, (doc, score) in enumerate(results, 1):
            meta = doc.metadata
            output += f"---\n**[Source {i}]** (Relevance: {score:.3f})\n"
            output += f"  File: {meta.get('filename', 'Unknown')}\n"
            output += f"  Page: {meta.get('page', 'N/A')}"
            if meta.get("section"):
                output += f" | Section: {meta['section']}"
            output += "\n"
            output += f"  Content:\n  {doc.page_content[:500]}\n\n"

        return output
    except Exception as e:
        return f"Error searching documents: {str(e)}"