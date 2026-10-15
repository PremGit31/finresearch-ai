# src/citations/citation_tracker.py
"""
Citation management — tracks source documents referenced in research output.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Citation:
    """A single citation linking a claim to a source."""
    citation_id: str
    source_type: str          # 'document', 'stock_data', 'news', 'calculation', 'sec_filing'
    source_name: str          # Filename or data source name
    page_or_section: str      # Page number or section reference
    content_excerpt: str      # Relevant excerpt
    relevance_score: float    # Relevance score from retrieval
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    url: Optional[str] = None


class CitationTracker:
    """Tracks all citations used during a research session."""

    def __init__(self):
        self.citations: list[Citation] = []
        self._counter = 0

    def add_citation(
        self,
        source_type: str,
        source_name: str,
        content_excerpt: str,
        page_or_section: str = "",
        relevance_score: float = 0.0,
        url: str | None = None,
    ) -> str:
        """Add a citation and return its reference ID."""
        self._counter += 1
        cid = f"[{self._counter}]"
        citation = Citation(
            citation_id=cid,
            source_type=source_type,
            source_name=source_name,
            page_or_section=page_or_section,
            content_excerpt=content_excerpt[:300],
            relevance_score=relevance_score,
            url=url,
        )
        self.citations.append(citation)
        return cid

    def add_citations_from_search_results(
        self, results: list[tuple], source_type: str = "document"
    ) -> list[str]:
        """Add multiple citations from vector search results."""
        cids = []
        for doc, score in results:
            meta = doc.metadata
            cid = self.add_citation(
                source_type=source_type,
                source_name=meta.get("filename", "Unknown"),
                content_excerpt=doc.page_content,
                page_or_section=f"Page {meta.get('page', '?')}, Section: {meta.get('section', 'N/A')}",
                relevance_score=score,
            )
            cids.append(cid)
        return cids

    def format_bibliography(self) -> str:
        """Format all citations as a bibliography section."""
        if not self.citations:
            return "\n## Sources\nNo sources cited.\n"

        output = "\n## Sources & Citations\n\n"
        for c in self.citations:
            output += f"**{c.citation_id}** "
            output += f"[{c.source_type.upper()}] {c.source_name}"
            if c.page_or_section:
                output += f" — {c.page_or_section}"
            output += f"\n"
            output += f"  Retrieved: {c.retrieved_at}\n"
            if c.url:
                output += f"  URL: {c.url}\n"
            output += f"  Excerpt: \"{c.content_excerpt[:150]}...\"\n"
            output += f"  Relevance: {c.relevance_score:.3f}\n\n"

        return output

    def get_citations_for_report(self) -> list[dict]:
        """Return citations as dictionaries for JSON serialization."""
        return [
            {
                "id": c.citation_id,
                "source_type": c.source_type,
                "source_name": c.source_name,
                "page_or_section": c.page_or_section,
                "excerpt": c.content_excerpt,
                "relevance_score": c.relevance_score,
                "url": c.url,
                "retrieved_at": c.retrieved_at,
            }
            for c in self.citations
        ]

    def clear(self):
        """Reset all citations."""
        self.citations.clear()
        self._counter = 0