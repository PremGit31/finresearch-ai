# src/agents/researcher.py
"""
Researcher node — gathers data from multiple sources.
"""
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.agents.state import ResearchState
from src.tools import (
    get_stock_price,
    get_stock_history,
    get_financial_ratios,
    search_financial_news,
    search_documents,
    get_sec_filings,
)
from src.citations.citation_tracker import CitationTracker
from src.agents.tool_calling import invoke_with_tools
from src.mcp.client import get_mcp_tools


def create_researcher_node():
    """Create the researcher node function for LangGraph."""

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )

    async def researcher_node(state: ResearchState) -> dict:
        """Research node that gathers data using tools."""
        query = state["query"]
        ticker = state["ticker"]
        previous_data = state.get("research_data", {})
        research_data = dict(previous_data)
        citations = list(state.get("citations", []))
        errors = list(state.get("errors", []))
        tracker = CitationTracker()
        try:
            mcp_tools = await get_mcp_tools()
        except Exception as exc:
            mcp_tools = []
            errors.append(f"MCP tool discovery failed: {exc}")

        tools = [
            *mcp_tools,
            get_stock_price,
            get_stock_history,
            get_financial_ratios,
            search_financial_news,
            search_documents,
            get_sec_filings,
        ]
        tool_names = ", ".join(tool.name for tool in tools)
        previous_text = "\n\n".join(
            f"### {name}\n{value}"
            for name, value in research_data.items()
            if isinstance(value, str)
        )
        prompt = f"""You are a financial research analyst gathering evidence for {ticker}.
Research question: {query}

Available tools: {tool_names}
Use the MCP stock quote and company financials tools, the MCP document search tool,
and relevant news/SEC/history tools when available. Do not invent results. If a
tool fails or returns no evidence, say so. Cite tool names and preserve important
numbers, dates, source links, and document excerpts in your synthesis.

Previously gathered data:
{previous_text[:5000] or "None"}

Return a concise, structured evidence summary with company/market context,
financial health, recent developments, risks, and opportunities."""
        synthesis, results, tool_errors = await invoke_with_tools(llm, tools, prompt)
        errors.extend(tool_errors)

        for item in results:
            key = item["name"]
            result = item["result"]
            existing = research_data.get(key)
            research_data[key] = (
                f"{existing}\n\n{result}" if isinstance(existing, str) else result
            )
            source_type = (
                "document" if "document" in key
                else "news" if "news" in key
                else "sec_filing" if "sec" in key
                else "stock_data"
            )
            tracker.add_citation(
                source_type=source_type,
                source_name=key,
                content_excerpt=result[:200],
            )

        citations.extend(tracker.get_citations_for_report())

        return {
            "research_data": research_data,
            "citations": citations,
            "errors": errors,
            "current_phase": "research_complete",
            "iteration_count": state.get("iteration_count", 0) + 1,
            "messages": [
                AIMessage(
                    content=f"Research phase complete. Gathered data from "
                    f"{len(research_data)} sources.\n\n{synthesis}"
                )
            ],
        }

    return researcher_node