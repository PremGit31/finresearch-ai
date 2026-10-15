# src/ingestion/chunker.py
"""
Intelligent document chunking for financial documents.
Uses semantic awareness — tries to keep tables, sections, paragraphs together.
"""
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


class FinancialDocumentChunker:
    """
    Chunks financial documents with awareness of:
    - Section headers (Item 1, Item 7, etc. for 10-K filings)
    - Tables and figures
    - Paragraph boundaries
    """

    # Financial section patterns
    SECTION_PATTERNS = [
        r"\n(?=Item\s+\d)",          # SEC filing items
        r"\n(?=PART\s+[IVX]+)",      # SEC filing parts
        r"\n(?=#{1,3}\s)",           # Markdown headers
        r"\n(?=[A-Z][A-Z\s]{10,}\n)", # ALL-CAPS section headers
    ]

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        # Build separators: financial sections first, then standard
        separators = self.SECTION_PATTERNS + [
            "\n\n\n",
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            is_separator_regex=True,
            length_function=len,
        )

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Chunk a list of documents, preserving and enriching metadata."""
        chunked = []
        for doc in documents:
            chunks = self.splitter.split_text(doc.page_content)
            for idx, chunk_text in enumerate(chunks):
                chunk_meta = {
                    **doc.metadata,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk_text),
                }

                # Detect section type
                section = self._detect_section(chunk_text)
                if section:
                    chunk_meta["section"] = section

                # Detect if chunk contains numerical/financial data
                chunk_meta["has_financial_data"] = self._has_financial_data(chunk_text)

                chunked.append(
                    Document(page_content=chunk_text, metadata=chunk_meta)
                )
        return chunked

    @staticmethod
    def _detect_section(text: str) -> str | None:
        """Try to identify which section of a filing this chunk belongs to."""
        patterns = {
            "business_overview": r"Item\s+1[.\s]",
            "risk_factors": r"Item\s+1A[.\s]",
            "financial_data": r"Item\s+6[.\s]",
            "md_and_a": r"Item\s+7[.\s]",
            "financial_statements": r"Item\s+8[.\s]",
            "controls": r"Item\s+9A[.\s]",
        }
        first_200 = text[:200]
        for section_name, pattern in patterns.items():
            if re.search(pattern, first_200, re.IGNORECASE):
                return section_name
        return None

    @staticmethod
    def _has_financial_data(text: str) -> bool:
        """Check if chunk contains financial numbers, tables, or ratios."""
        # Look for dollar amounts, percentages, or table-like structures
        financial_patterns = [
            r"\$[\d,]+\.?\d*",          # Dollar amounts
            r"\d+\.?\d*\s*%",           # Percentages
            r"(?:revenue|income|ebitda|eps|earnings)", # Financial terms
            r"\d{1,3}(?:,\d{3})+",      # Large numbers with commas
        ]
        for pattern in financial_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False