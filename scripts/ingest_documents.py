# scripts/ingest_documents.py
"""
Script to ingest financial documents from the data/raw directory.
Usage: python scripts/ingest_documents.py [--directory path/to/docs]
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import RAW_DIR
from src.ingestion.document_loader import FinancialDocumentLoader
from src.ingestion.chunker import FinancialDocumentChunker
from src.vectorstore.qdrant_store import FinancialVectorStore


def ingest(directory: str, company: str = None, doc_type: str = None):
    """Ingest all documents from a directory."""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory {dir_path} does not exist.")
        return

    print(f"📂 Scanning directory: {dir_path}")

    loader = FinancialDocumentLoader()
    chunker = FinancialDocumentChunker()
    vector_store = FinancialVectorStore()

    metadata = {}
    if company:
        metadata["company"] = company
    if doc_type:
        metadata["document_type"] = doc_type

    # Load documents
    documents = loader.load_directory(dir_path, metadata)
    print(f"📄 Loaded {len(documents)} document pages")

    if not documents:
        print("No documents found to ingest.")
        return

    # Chunk documents
    chunks = chunker.chunk_documents(documents)
    print(f"🔪 Created {len(chunks)} chunks")

    # Index in vector store
    print("📊 Indexing in Qdrant...")
    ids = vector_store.add_documents(chunks)
    print(f"✅ Indexed {len(ids)} chunks in Qdrant")

    # Print summary
    info = vector_store.get_collection_info()
    print(f"\n📈 Collection Info:")
    print(f"   Name: {info['name']}")
    print(f"   Total Vectors: {info['vectors_count']}")
    print(f"   Status: {info['status']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest financial documents")
    parser.add_argument(
        "--directory", "-d", default=str(RAW_DIR), help="Directory containing documents"
    )
    parser.add_argument("--company", "-c", help="Company name for metadata")
    parser.add_argument("--type", "-t", dest="doc_type", help="Document type")

    args = parser.parse_args()
    ingest(args.directory, args.company, args.doc_type)