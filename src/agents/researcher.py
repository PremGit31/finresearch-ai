# src/agents/researcher.py
"""
Researcher node — gathers data from multiple sources.
"""
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

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


RESEARCHER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a Senior Financial Research Analyst. Your job is to gather 
comprehensive data about companies and financial topics.

You have access to the following tools:
- get_stock_price: Get current stock price and market data
- get_stock_history: Get historical price data
- get_financial_ratios: Get financial ratios and fundamentals
- search_financial_news: Search for recent financial news
- search_documents: Search through ingested financial documents (annual reports, transcripts, filings)
- get_sec_filings: Search SEC EDGAR for company filings

Strategy:
1. Start by getting current stock price and financial ratios
2. Search for recent news and developments
3. Search through ingested documents for relevant information
4. Check SEC filings for recent submissions
5. Compile all findings systematically

Be thorough. Gather data from ALL available sources. Mark each piece of data with its source 
for citation purposes.
"""),
    ("human", """Research the following query:

**Query:** {query}
**Ticker:** {ticker}

Previous research data (if any):
{previous_data}

Gather comprehensive data to answer this query. Use all available tools.
"""),
])


def create_researcher_node():
    """Create the researcher node function for LangGraph."""

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )

    tools = [
        get_stock_price,
        get_stock_history,
        get_financial_ratios,
        search_financial_news,
        search_documents,
        get_sec_filings,
    ]

    llm_with_tools = llm.bind_tools(tools)

    async def researcher_node(state: ResearchState) -> dict:
        """Research node that gathers data using tools."""
        query = state["query"]
        ticker = state["ticker"]
        previous_data = state.get("research_data", {})

        # Collect data from each tool
        research_data = dict(previous_data)
        citations = list(state.get("citations", []))
        errors = list(state.get("errors", []))
        tracker = CitationTracker()

        # 1. Stock price
        try:
            price_data = get_stock_price.invoke({"ticker": ticker})
            research_data["stock_price"] = price_data
            cid = tracker.add_citation(
                source_type="stock_data",
                source_name=f"Yahoo Finance — {ticker}",
                content_excerpt=price_data[:200],
            )
        except Exception as e:
            errors.append(f"Stock price error: {e}")

        # 2. Financial ratios
        try:
            ratios_data = get_financial_ratios.invoke({"ticker": ticker})
            research_data["financial_ratios"] = ratios_data
            tracker.add_citation(
                source_type="stock_data",
                source_name=f"Financial Ratios — {ticker}",
                content_excerpt=ratios_data[:200],
            )
        except Exception as e:
            errors.append(f"Financial ratios error: {e}")

        # 3. Stock history
        try:
            history_data = get_stock_history.invoke(
                {"ticker": ticker, "period": "3mo"}
            )
            research_data["stock_history"] = history_data
            tracker.add_citation(
                source_type="stock_data",
                source_name=f"Price History — {ticker}",
                content_excerpt=history_data[:200],
            )
        except Exception as e:
            errors.append(f"Stock history error: {e}")

        # 4. News
        try:
            news_data = search_financial_news.invoke(
                {"query": f"{ticker} stock", "max_results": 8}
            )
            research_data["news"] = news_data
            tracker.add_citation(
                source_type="news",
                source_name="Financial News Aggregation",
                content_excerpt=news_data[:200],
            )
        except Exception as e:
            errors.append(f"News search error: {e}")

        # 5. Document search (RAG)
        try:
            doc_results = search_documents.invoke(
                {"query": query, "num_results": 5}
            )
            research_data["document_search"] = doc_results
            tracker.add_citation(
                source_type="document",
                source_name="Internal Document Search",
                content_excerpt=doc_results[:200],
            )
        except Exception as e:
            errors.append(f"Document search error: {e}")

        # 6. SEC filings
        try:
            filings_data = get_sec_filings.invoke(
                {"ticker": ticker, "filing_type": "10-K", "max_results": 3}
            )
            research_data["sec_filings"] = filings_data
            tracker.add_citation(
                source_type="sec_filing",
                source_name=f"SEC EDGAR — {ticker}",
                content_excerpt=filings_data[:200],
            )
        except Exception as e:
            errors.append(f"SEC filings error: {e}")

        # Use LLM to synthesize a research summary
        data_summary = "\n\n".join(
            f"### {k.replace('_', ' ').title()}\n{v}"
            for k, v in research_data.items()
            if isinstance(v, str)
        )

        synthesis_prompt = f"""Based on the following raw research data, provide a structured 
research summary for the query: "{query}" about {ticker}.

Organize the information into:
1. Company Overview
2. Current Market Position
3. Financial Health
4. Recent Developments
5. Key Risks
6. Key Opportunities

Raw Data:
{data_summary[:8000]}
"""

        response = await llm.ainvoke([HumanMessage(content=synthesis_prompt)])

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
                    f"{len(research_data)} sources.\n\n{response.content}"
                )
            ],
        }

    return researcher_node