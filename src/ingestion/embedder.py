# src/ingestion/embedder.py
"""
Embedding pipeline using Google's gemini-embedding-001 model.
"""
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config.settings import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    """Return the configured embedding model."""
    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
    )