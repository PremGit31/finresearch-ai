# src/agents/analyst.py
"""
Analyst node — performs deep analysis on research data.
"""
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.agents.state import ResearchState
from src.tools.calculator import financial_calculator
from src.agents.tool_calling import invoke_with_tools
from src.mcp.client import get_mcp_tools


ANALYST_SYSTEM_PROMPT = """You are a Senior Financial Analyst at a top-tier investment bank.

Your job is to analyze the research data and produce a rigorous, evidence-based investment analysis.

You must:
1. Analyze financial health using key ratios and metrics
2. Evaluate growth trajectory and market position
3. Assess valuation (overvalued/undervalued/fairly valued)
4. Identify catalysts and risks
5. Compare to industry benchmarks where possible
6. Provide a clear investment thesis with supporting evidence
7. Reference specific data points with citation markers [1], [2], etc.

Use the financial_calculator tool for any calculations you need (DCF, CAGR, WACC, etc.)

Be analytical, not promotional. Present both bull and bear cases.
"""


def create_analyst_node():
    """Create the analyst node function for LangGraph."""

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.2,
    )

    async def analyst_node(state: ResearchState) -> dict:
        """Analyst node that performs deep financial analysis."""
        query = state["query"]
        ticker = state["ticker"]
        research_data = state.get("research_data", {})

        # Compile research data into analysis input
        data_text = ""
        for key, value in research_data.items():
            if isinstance(value, str):
                data_text += f"\n### {key.replace('_', ' ').title()}\n{value}\n"

        errors = list(state.get("errors", []))
        try:
            mcp_tools = await get_mcp_tools()
        except Exception as exc:
            mcp_tools = []
            errors.append(f"Analyst MCP tool discovery failed: {exc}")

        tools = [financial_calculator, *mcp_tools]
        analysis_prompt = f"""{ANALYST_SYSTEM_PROMPT}

**Research Query:** {query}
**Company:** {ticker}

**Research Data:**
{data_text[:12000]}

Use MCP company financials, stock quote, and document-search tools when useful to
independently inspect source data. Use the financial_calculator tool for any
quantitative calculation you cite, and include the exact inputs and returned result
in a "Calculation checks" section. If a source or calculation is unavailable, state
that limitation instead of estimating. Produce a balanced analysis with sections,
specific numbers, citations, and a checkable-claims section.
"""

        analysis, _, tool_errors = await invoke_with_tools(
            llm, tools, analysis_prompt
        )
        errors.extend(tool_errors)

        return {
            "analysis": analysis,
            "errors": errors,
            "current_phase": "analysis_complete",
            "messages": [
                AIMessage(
                    content=f"Analysis phase complete.\n\n{analysis[:500]}..."
                )
            ],
        }

    return analyst_node