# tests/test_agents.py
"""
Tests for agent components.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.agents.state import ResearchState
from src.citations.citation_tracker import CitationTracker


class TestCitationTracker:
    def test_add_citation(self):
        tracker = CitationTracker()
        cid = tracker.add_citation(
            source_type="document",
            source_name="AAPL_10K_2024.pdf",
            content_excerpt="Revenue increased to $94.9 billion",
            page_or_section="Page 5",
            relevance_score=0.95,
        )
        assert cid == "[1]"
        assert len(tracker.citations) == 1

    def test_multiple_citations(self):
        tracker = CitationTracker()
        cid1 = tracker.add_citation(
            source_type="document",
            source_name="doc1.pdf",
            content_excerpt="test1",
        )
        cid2 = tracker.add_citation(
            source_type="news",
            source_name="Reuters",
            content_excerpt="test2",
        )
        assert cid1 == "[1]"
        assert cid2 == "[2]"

    def test_format_bibliography(self):
        tracker = CitationTracker()
        tracker.add_citation(
            source_type="document",
            source_name="report.pdf",
            content_excerpt="Financial data",
            page_or_section="Page 10",
            relevance_score=0.9,
        )
        bib = tracker.format_bibliography()
        assert "Sources & Citations" in bib
        assert "report.pdf" in bib
        assert "DOCUMENT" in bib

    def test_clear(self):
        tracker = CitationTracker()
        tracker.add_citation(
            source_type="test",
            source_name="test",
            content_excerpt="test",
        )
        assert len(tracker.citations) == 1
        tracker.clear()
        assert len(tracker.citations) == 0

    def test_get_citations_for_report(self):
        tracker = CitationTracker()
        tracker.add_citation(
            source_type="document",
            source_name="doc.pdf",
            content_excerpt="content",
            url="https://example.com",
        )
        citations = tracker.get_citations_for_report()
        assert len(citations) == 1
        assert citations[0]["source_name"] == "doc.pdf"
        assert citations[0]["url"] == "https://example.com"


class TestResearchState:
    def test_state_structure(self):
        state: ResearchState = {
            "query": "Analyze AAPL",
            "ticker": "AAPL",
            "messages": [],
            "research_data": {},
            "analysis": "",
            "fact_check_results": {},
            "final_report": "",
            "citations": [],
            "current_phase": "starting",
            "iteration_count": 0,
            "needs_more_research": False,
            "errors": [],
        }
        assert state["ticker"] == "AAPL"
        assert state["current_phase"] == "starting"