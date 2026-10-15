# api/routes/research.py
"""
Research endpoints — trigger and retrieve research reports.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from api.models.schemas import ResearchRequest, ResearchResponse
from src.agents.graph import research_graph
from src.agents.state import ResearchState
from src.tools.document_search import set_vector_store
from src.vectorstore.qdrant_store import FinancialVectorStore

router = APIRouter(prefix="/research", tags=["research"])

# Initialize vector store for document search tool
try:
    _vs = FinancialVectorStore()
    set_vector_store(_vs)
except Exception:
    pass  # Will work without vector store, just no document search


@router.post("/analyze", response_model=ResearchResponse)
async def analyze_company(request: ResearchRequest):
    """
    Run a full research analysis on a company.

    This triggers the multi-agent LangGraph workflow:
    1. Researcher gathers data from all sources
    2. Analyst performs deep financial analysis
    3. Fact-checker validates claims
    4. Report writer compiles the final report
    """
    try:
        # Build initial state
        initial_state: ResearchState = {
            "query": request.query,
            "ticker": request.ticker.upper(),
            "messages": [
                HumanMessage(
                    content=f"Research {request.ticker}: {request.query}"
                )
            ],
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

        # Run the graph
        result = await research_graph.ainvoke(initial_state)

        # Collect phases
        phases = []
        if result.get("research_data"):
            phases.append("research")
        if result.get("analysis"):
            phases.append("analysis")
        if result.get("fact_check_results"):
            phases.append("fact_check")
        if result.get("final_report"):
            phases.append("report_generation")

        return ResearchResponse(
            status="complete",
            ticker=request.ticker.upper(),
            query=request.query,
            report=result.get("final_report", "Report generation failed."),
            citations=result.get("citations", []),
            fact_check=result.get("fact_check_results", {}),
            phases_completed=phases,
            errors=result.get("errors", []),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Research analysis failed: {str(e)}",
        )


@router.post("/quick-quote")
async def quick_stock_quote(ticker: str):
    """Get a quick stock quote without full analysis."""
    from src.tools.stock_price import get_stock_price
    try:
        result = get_stock_price.invoke({"ticker": ticker})
        return {"ticker": ticker.upper(), "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))