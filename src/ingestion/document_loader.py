# src/ingestion/document_loader.py
"""
Document loader for financial documents — PDFs, HTML filings, text transcripts.
"""
import hashlib
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from pypdf import PdfReader
from bs4 import BeautifulSoup


class FinancialDocumentLoader:
    """Loads financial documents with rich metadata extraction."""

    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".html", ".htm", ".md"}

    def __init__(self):
        self._loaders = {
            ".pdf": self._load_pdf,
            ".txt": self._load_text,
            ".html": self._load_html,
            ".htm": self._load_html,
            ".md": self._load_text,
        }

    def load(
        self,
        file_path: str | Path,
        metadata: Optional[dict] = None,
    ) -> list[Document]:
        """Load a single document with metadata."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {ext}. Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        loader_fn = self._loaders[ext]
        pages = loader_fn(file_path)

        # Compute document hash for deduplication
        file_hash = self._compute_hash(file_path)

        base_metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "file_type": ext,
            "file_hash": file_hash,
        }
        if metadata:
            base_metadata.update(metadata)

        documents = []
        for i, page_content in enumerate(pages):
            if not page_content.strip():
                continue
            doc_meta = {**base_metadata, "page": i + 1, "total_pages": len(pages)}
            documents.append(Document(page_content=page_content, metadata=doc_meta))

        return documents

    def load_directory(
        self,
        directory: str | Path,
        metadata: Optional[dict] = None,
    ) -> list[Document]:
        """Load all supported documents from a directory."""
        directory = Path(directory)
        all_docs = []
        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in directory.glob(f"*{ext}"):
                try:
                    docs = self.load(file_path, metadata)
                    all_docs.extend(docs)
                except Exception as e:
                    print(f"Warning: Failed to load {file_path}: {e}")
        return all_docs

    def _load_pdf(self, file_path: Path) -> list[str]:
        """Extract text from each page of a PDF."""
        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return pages

    def _load_text(self, file_path: Path) -> list[str]:
        """Load plain text file as a single page."""
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return [text]

    def _load_html(self, file_path: Path) -> list[str]:
        """Parse HTML (SEC filings are often HTML) and extract text."""
        raw_html = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw_html, "lxml")

        # Remove script and style tags
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return [text]

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        """Compute SHA-256 hash for deduplication."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]