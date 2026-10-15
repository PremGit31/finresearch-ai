# src/vectorstore/qdrant_store.py
"""
Qdrant vector store operations — indexing, search, management.
"""
from typing import Optional
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config.settings import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
from src.ingestion.embedder import get_embedding_model


class FinancialVectorStore:
    """Manages the Qdrant vector store for financial documents."""

    def __init__(
        self,
        collection_name: str = QDRANT_COLLECTION,
        host: str = QDRANT_HOST,
        port: int = QDRANT_PORT,
    ):
        self.collection_name = collection_name
        self.embeddings = get_embedding_model()
        self.client = QdrantClient(host=host, port=port)
        self._ensure_collection()
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=3072,  # gemini-embedding-001 output dimension
                    distance=Distance.COSINE,
                ),
            )

    def add_documents(self, documents: list[Document]) -> list[str]:
        """Add documents to the vector store. Returns list of IDs."""
        ids = self.vector_store.add_documents(documents)
        return ids

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[Document]:
        """Search for similar documents."""
        kwargs = {"k": k}
        if filter_metadata:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            conditions = []
            for key, value in filter_metadata.items():
                conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value),
                    )
                )
            kwargs["filter"] = Filter(must=conditions)
        return self.vector_store.similarity_search(query, **kwargs)

    def similarity_search_with_score(
        self, query: str, k: int = 5
    ) -> list[tuple[Document, float]]:
        """Search with relevance scores."""
        return self.vector_store.similarity_search_with_score(query, k=k)

    def get_collection_info(self) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
        }

    def delete_collection(self):
        """Delete the entire collection."""
        self.client.delete_collection(self.collection_name)

    def as_retriever(self, k: int = 5):
        """Return a LangChain retriever interface."""
        return self.vector_store.as_retriever(search_kwargs={"k": k})