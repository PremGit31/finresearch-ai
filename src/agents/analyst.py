# src/agents/analyst.py
"""
Analyst node — performs deep analysis on research data.
"""
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.agents.state import ResearchState
from src.tools.calculator import financial_calculator


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

    tools = [financial_calculator]
    llm_with_tools = llm.bind_tools(tools)

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

        analysis_prompt = f"""{ANALYST_SYSTEM_PROMPT}

**Research Query:** {query}
**Company:** {ticker}

**Research Data:**
{data_text[:12000]}

Produce a comprehensive investment analysis. Include specific numbers, ratios, and 
cite your sources using [Source X] markers. Structure your analysis with clear sections.

If you need to perform calculations (DCF, CAGR, etc.), describe what you would calculate 
and provide the analysis based on the available data.
"""

        response = await llm.ainvoke([HumanMessage(content=analysis_prompt)])

        analysis = response.content

        return {
            "analysis": analysis,
            "current_phase": "analysis_complete",
            "messages": [
                AIMessage(
                    content=f"Analysis phase complete.\n\n{analysis[:500]}..."
                )
            ],
        }

    return analyst_node