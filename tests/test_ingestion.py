# tests/test_ingestion.py
"""
Tests for document ingestion pipeline.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import tempfile
from src.ingestion.document_loader import FinancialDocumentLoader
from src.ingestion.chunker import FinancialDocumentChunker


class TestDocumentLoader:
    def setup_method(self):
        self.loader = FinancialDocumentLoader()

    def test_load_text_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a test financial document.\n" * 10)
            f.flush()
            docs = self.loader.load(f.name)
            assert len(docs) > 0
            assert "test financial document" in docs[0].page_content
            assert "file_hash" in docs[0].metadata

    def test_load_with_metadata(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Revenue increased 15% year over year.\n")
            f.flush()
            docs = self.loader.load(
                f.name,
                metadata={"company": "TestCorp", "year": "2024"},
            )
            assert docs[0].metadata["company"] == "TestCorp"
            assert docs[0].metadata["year"] == "2024"

    def test_unsupported_file_type(self):
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            f.flush()
            with pytest.raises(ValueError, match="Unsupported"):
                self.loader.load(f.name)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.loader.load("/nonexistent/path/file.txt")


class TestChunker:
    def setup_method(self):
        self.chunker = FinancialDocumentChunker(chunk_size=200, chunk_overlap=50)

    def test_chunk_documents(self):
        from langchain_core.documents import Document

        long_text = "This is a paragraph about financial performance. " * 50
        docs = [Document(page_content=long_text, metadata={"source": "test"})]

        chunks = self.chunker.chunk_documents(docs)
        assert len(chunks) > 1
        assert all("chunk_index" in c.metadata for c in chunks)

    def test_financial_data_detection(self):
        from langchain_core.documents import Document

        doc = Document(
            page_content="Revenue was $45.2 billion, up 12.5% year over year.",
            metadata={"source": "test"},
        )
        chunks = self.chunker.chunk_documents([doc])
        assert chunks[0].metadata["has_financial_data"] is True

    def test_non_financial_data(self):
        from langchain_core.documents import Document

        doc = Document(
            page_content="The company was founded in a small garage many years ago.",
            metadata={"source": "test"},
        )
        chunks = self.chunker.chunk_documents([doc])
        assert chunks[0].metadata["has_financial_data"] is False

    def test_section_detection(self):
        text = "Item 1A. Risk Factors\n\nThe company faces several risks..."
        section = self.chunker._detect_section(text)
        assert section == "risk_factors"