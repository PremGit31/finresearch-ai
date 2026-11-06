"""Fact-check claims against independently retrieved evidence."""
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.agents.state import ResearchState
from src.mcp.client import get_mcp_tools


class CalculationCheck(BaseModel):
    calculation_type: Literal["growth_rate", "cagr", "ratio"]
    inputs: dict[str, float]
    claimed_value: float
    tolerance: float = Field(default=0.01, gt=0)


class ClaimToVerify(BaseModel):
    statement: str
    evidence_query: str
    calculation: CalculationCheck | None = None


class ClaimExtraction(BaseModel):
    claims: list[ClaimToVerify]


class ClaimVerdict(BaseModel):
    statement: str
    status: Literal["verified", "contradicted", "not_found", "inconclusive"]
    rationale: str
    evidence: str = ""


class VerdictBundle(BaseModel):
    claims: list[ClaimVerdict]


def recompute_calculation(check: CalculationCheck) -> dict:
    """Recompute a supported formula without evaluating model-generated code."""
    inputs = check.inputs
    if check.calculation_type == "growth_rate":
        old_value = inputs["old_value"]
        if old_value == 0:
            raise ValueError("Growth rate requires a non-zero old_value.")
        result = (inputs["new_value"] - old_value) / old_value * 100
    elif check.calculation_type == "cagr":
        beginning = inputs["beginning_value"]
        ending = inputs["ending_value"]
        years = inputs["years"]
        if beginning <= 0 or ending < 0 or years <= 0:
            raise ValueError("CAGR requires positive beginning value and years.")
        result = ((ending / beginning) ** (1 / years) - 1) * 100
    else:
        denominator = inputs["denominator"]
        if denominator == 0:
            raise ValueError("A ratio requires a non-zero denominator.")
        result = inputs["numerator"] / denominator

    difference = abs(result - check.claimed_value)
    return {
        "calculated_value": result,
        "claimed_value": check.claimed_value,
        "matches": difference <= check.tolerance,
        "tolerance": check.tolerance,
    }


def create_fact_checker_node():
    """Create the graph node that re-fetches evidence and checks claim arithmetic."""
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )
    claim_extractor = llm.with_structured_output(ClaimExtraction)
    verifier = llm.with_structured_output(VerdictBundle)

    async def fact_checker_node(state: ResearchState) -> dict:
        analysis = state.get("analysis", "")
        errors = list(state.get("errors", []))
        extraction = await claim_extractor.ainvoke(
            f"""Extract at most 8 externally checkable factual claims from this
financial analysis. Prefer claims containing a number, date, financial metric,
or assertion about the company. Exclude opinions, recommendations, and forecasts
that cannot be verified from historical/source data. For every claim, provide a
focused evidence_query suitable for an independent document search.

If a claim reports a growth rate, CAGR, or ratio and the analysis provides its
inputs, include a calculation using percent units for growth/CAGR and multiple
units for ratios. Include the exact input values, the claimed result, and a
reasonable absolute tolerance. Do not invent missing operands.

Analysis:
{analysis}"""
        )
        claims = extraction.claims[:8]
        if not claims:
            fact_check_results = {
                "report": "No independently checkable factual claims were extracted.",
                "claims": [],
                "needs_revision": False,
                "needs_more_research": False,
            }
            return {
                "fact_check_results": fact_check_results,
                "needs_more_research": False,
                "current_phase": "fact_check_complete",
                "messages": [AIMessage(content=fact_check_results["report"])],
                "errors": errors,
            }

        evidence_by_claim = []
        search_tool = None
        evidence_retrieval_failed = False
        financial_data = {}
        try:
            mcp_tools = await get_mcp_tools()
            search_tool = next(
                (tool for tool in mcp_tools if tool.name == "search_financial_documents"),
                None,
            )
            if search_tool is None:
                evidence_retrieval_failed = True
                errors.append("MCP document search tool was not discovered for fact-checking.")
        except Exception as exc:
            mcp_tools = []
            evidence_retrieval_failed = True
            errors.append(f"Fact-check MCP tool discovery failed: {exc}")

        for tool_name in ("company_financials", "stock_quote"):
            tool = next(
                (candidate for candidate in mcp_tools if candidate.name == tool_name),
                None,
            )
            if tool is not None:
                try:
                    financial_data[tool_name] = await tool.ainvoke({
                        "ticker": state["ticker"],
                    })
                except Exception as exc:
                    financial_data[tool_name] = f"Independent lookup failed: {exc}"
                    errors.append(f"Fact-check {tool_name} lookup failed: {exc}")

        for claim in claims:
            if search_tool is None:
                evidence = "Independent document search unavailable."
            else:
                try:
                    evidence = await search_tool.ainvoke({
                        "query": claim.evidence_query,
                        "num_results": 3,
                    })
                except Exception as exc:
                    evidence_retrieval_failed = True
                    evidence = f"Independent evidence retrieval failed: {exc}"
                    errors.append(
                        f"Evidence retrieval failed for claim '{claim.statement}': {exc}"
                    )
            evidence_by_claim.append({
                "statement": claim.statement,
                "evidence_query": claim.evidence_query,
                "evidence": str(evidence),
            })

        verdicts = await verifier.ainvoke(
            f"""Verify each claim using only its independently retrieved evidence
below. Do not treat the claim, analyst narrative, or prior research summary as
evidence. Preserve each statement exactly and return one verdict for every claim.

Use "verified" only when the evidence directly supports the statement; use
"contradicted" when evidence conflicts; "not_found" when a usable source was
searched but does not support it; and "inconclusive" when evidence is unavailable
or ambiguous. Keep evidence excerpts concise and identify the source when shown.

Claims and independently retrieved evidence:
{evidence_by_claim}

Additional independently fetched MCP company/market data for {state["ticker"]}:
{financial_data}"""
        )
        verdict_map = {verdict.statement: verdict for verdict in verdicts.claims}
        checks = []
        for claim, retrieved in zip(claims, evidence_by_claim):
            verdict = verdict_map.get(claim.statement)
            status = verdict.status if verdict else "inconclusive"
            rationale = verdict.rationale if verdict else "No verdict returned for this claim."
            evidence_excerpt = verdict.evidence if verdict else retrieved["evidence"]
            calculation = None
            if claim.calculation is not None:
                try:
                    calculation = recompute_calculation(claim.calculation)
                    if not calculation["matches"]:
                        status = "contradicted"
                        rationale += (
                            " Deterministic recomputation does not match the claimed result."
                        )
                except (KeyError, ValueError) as exc:
                    calculation = {"error": str(exc)}
                    if status == "verified":
                        status = "inconclusive"
                        rationale += " Calculation could not be independently recomputed."
            checks.append({
                "statement": claim.statement,
                "status": status,
                "rationale": rationale,
                "evidence_query": claim.evidence_query,
                "evidence": evidence_excerpt,
                "calculation": calculation,
            })

        needs_more = not evidence_retrieval_failed and any(
            item["status"] == "not_found" for item in checks
        )
        needs_revision = any(
            item["status"] in {"contradicted", "not_found", "inconclusive"}
            for item in checks
        )
        report_lines = ["Independent claim verification:"]
        for index, item in enumerate(checks, 1):
            report_lines.append(
                f"{index}. [{item['status'].upper()}] {item['statement']}\n"
                f"   Rationale: {item['rationale']}\n"
                f"   Evidence: {item['evidence']}"
            )
            if item["calculation"] is not None:
                report_lines.append(f"   Recalculation: {item['calculation']}")
        report = "\n".join(report_lines)
        fact_check_results = {
            "report": report,
            "claims": checks,
            "needs_revision": needs_revision,
            "needs_more_research": needs_more,
        }

        return {
            "fact_check_results": fact_check_results,
            "needs_more_research": needs_more,
            "current_phase": "fact_check_complete",
            "messages": [AIMessage(content=report[:1000])],
            "errors": errors,
        }

    return fact_checker_node
