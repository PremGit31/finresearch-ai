# src/agents/fact_checker.py
"""
Fact-checker node — validates claims and checks for consistency.
"""
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.agents.state import ResearchState


FACT_CHECKER_PROMPT = """You are a meticulous Financial Fact Checker. Your role is to:

1. Review the analysis for factual accuracy
2. Check that cited numbers match the research data
3. Identify any unsupported claims
4. Flag logical inconsistencies
5. Verify that the investment thesis follows from the evidence
6. Check for common analytical errors (survivorship bias, recency bias, etc.)

For each claim in the analysis, mark it as:
- ✅ VERIFIED: Supported by the research data
- ⚠️ PARTIALLY VERIFIED: Some support but needs qualification
- ❌ UNVERIFIED: No supporting evidence found
- 🔄 NEEDS MORE DATA: Additional research needed

Provide a fact-check score (0-100) indicating overall reliability.
"""


def create_fact_checker_node():
    """Create the fact-checker node function for LangGraph."""

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )

    async def fact_checker_node(state: ResearchState) -> dict:
        """Fact-checker node that validates the analysis."""
        analysis = state.get("analysis", "")
        research_data = state.get("research_data", {})

        # Build verification context
        data_summary = ""
        for key, value in research_data.items():
            if isinstance(value, str):
                data_summary += f"\n### {key}\n{value[:1000]}\n"

        prompt = f"""{FACT_CHECKER_PROMPT}

**Analysis to Fact-Check:**
{analysis}

**Available Research Data:**
{data_summary[:8000]}

Provide your fact-check report. End with:
- Overall Reliability Score: X/100
- Recommendation: [PUBLISH / REVISE / NEEDS_MORE_RESEARCH]
"""

        response = await llm.ainvoke([HumanMessage(content=prompt)])

        fact_check_text = response.content

        # Parse recommendation
        needs_more = "NEEDS_MORE_RESEARCH" in fact_check_text.upper()
        needs_revision = "REVISE" in fact_check_text.upper()

        fact_check_results = {
            "report": fact_check_text,
            "needs_revision": needs_revision,
            "needs_more_research": needs_more,
        }

        return {
            "fact_check_results": fact_check_results,
            "needs_more_research": needs_more and state.get("iteration_count", 0) < 3,
            "current_phase": "fact_check_complete",
            "messages": [
                AIMessage(
                    content=f"Fact-check complete.\n\n{fact_check_text[:500]}..."
                )
            ],
        }

    return fact_checker_node