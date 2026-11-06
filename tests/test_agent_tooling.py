"""Tests for graph tool execution, MCP use, and independent claim checks."""
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from src.agents.fact_checker import (
    CalculationCheck,
    ClaimExtraction,
    ClaimToVerify,
    VerdictBundle,
    ClaimVerdict,
    create_fact_checker_node,
    recompute_calculation,
)
from src.agents.tool_calling import (
    invoke_with_tools,
    stringify_model_content,
    stringify_tool_result,
)


class FakeTool:
    def __init__(self, name, result):
        self.name = name
        self.result = result
        self.calls = []

    async def ainvoke(self, arguments):
        self.calls.append(arguments)
        return self.result


class ToolCallingLLM:
    def __init__(self, tool_name, tool_arguments, expected_result="Retrieved MCP evidence"):
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments
        self.expected_result = expected_result
        self.calls = 0

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                additional_kwargs={"thought_signature": "opaque-signature"},
                tool_calls=[{
                    "name": self.tool_name,
                    "args": self.tool_arguments,
                    "id": "tool-call-1",
                    "type": "tool_call",
                }],
            )
        assistant_message = next(
            message for message in messages if isinstance(message, AIMessage)
        )
        assert assistant_message.additional_kwargs["thought_signature"] == "opaque-signature"
        assert messages[-1].content == self.expected_result
        return AIMessage(content="Research summary")


@pytest.mark.asyncio
async def test_tool_call_loop_executes_tool_and_returns_its_evidence():
    tool = FakeTool("search_financial_documents", "Retrieved MCP evidence")
    llm = ToolCallingLLM("search_financial_documents", {"query": "revenue"})

    answer, results, errors = await invoke_with_tools(
        llm, [tool], "Find the revenue evidence."
    )

    assert answer == "Research summary"
    assert results[0]["result"] == "Retrieved MCP evidence"
    assert tool.calls == [{"query": "revenue"}]
    assert errors == []


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("Report text", "Report text"),
        ([{"type": "text", "text": "Report text"}], "Report text"),
        (["First paragraph", {"type": "text", "text": "Second paragraph"}],
         "First paragraph\nSecond paragraph"),
    ],
)
def test_stringify_model_content_handles_text_blocks(content, expected):
    assert stringify_model_content(content) == expected


@pytest.mark.parametrize(
    "result",
    [
        {"income_statement": {"Interest Income": float("nan")}},
        '{"income_statement": {"Interest Income": NaN, "Interest Expense": Infinity}}',
    ],
)
def test_stringify_tool_result_converts_non_finite_values_to_null(result):
    serialized = stringify_tool_result(result)

    assert '"Interest Income": null' in serialized
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


@pytest.mark.asyncio
async def test_researcher_can_execute_a_discovered_mcp_tool(monkeypatch):
    import src.agents.researcher as researcher

    mcp_tool = FakeTool("stock_quote", '{"ticker": "AAPL", "price": 200}')
    llm = ToolCallingLLM(
        "stock_quote",
        {"ticker": "AAPL"},
        expected_result='{"ticker": "AAPL", "price": 200}',
    )
    monkeypatch.setattr(researcher, "ChatGoogleGenerativeAI", lambda **kwargs: llm)

    async def discover_tools():
        return [mcp_tool]

    monkeypatch.setattr(researcher, "get_mcp_tools", discover_tools)
    node = researcher.create_researcher_node()
    result = await node({
        "query": "Check the latest quote",
        "ticker": "AAPL",
        "research_data": {},
        "citations": [],
        "errors": [],
        "iteration_count": 0,
    })

    assert mcp_tool.calls == [{"ticker": "AAPL"}]
    assert "stock_quote" in result["research_data"]
    assert result["citations"][0]["source_name"] == "stock_quote"


@pytest.mark.asyncio
async def test_analyst_can_execute_a_discovered_mcp_tool(monkeypatch):
    import src.agents.analyst as analyst

    mcp_tool = FakeTool("company_financials", '{"income_statement": {"Revenue": 100}}')
    llm = ToolCallingLLM(
        "company_financials",
        {"ticker": "AAPL"},
        expected_result='{"income_statement": {"Revenue": 100}}',
    )
    monkeypatch.setattr(analyst, "ChatGoogleGenerativeAI", lambda **kwargs: llm)

    async def discover_tools():
        return [mcp_tool]

    monkeypatch.setattr(analyst, "get_mcp_tools", discover_tools)
    node = analyst.create_analyst_node()
    result = await node({
        "query": "Analyze financial health",
        "ticker": "AAPL",
        "research_data": {},
        "errors": [],
    })

    assert mcp_tool.calls == [{"ticker": "AAPL"}]
    assert result["analysis"] == "Research summary"


@pytest.mark.parametrize(
    ("calculation_type", "inputs", "claimed_value", "expected"),
    [
        ("growth_rate", {"old_value": 100, "new_value": 120}, 20, 20),
        ("cagr", {"beginning_value": 100, "ending_value": 121, "years": 2}, 10, 10),
        ("ratio", {"numerator": 30, "denominator": 10}, 3, 3),
    ],
)
def test_recompute_supported_calculations(
    calculation_type, inputs, claimed_value, expected
):
    check = CalculationCheck(
        calculation_type=calculation_type,
        inputs=inputs,
        claimed_value=claimed_value,
    )
    result = recompute_calculation(check)

    assert result["calculated_value"] == pytest.approx(expected)
    assert result["matches"] is True


class StructuredFakeLLM:
    def __init__(self):
        self.verification_prompt = ""

    def with_structured_output(self, schema):
        async def ainvoke(prompt):
            if schema is ClaimExtraction:
                return ClaimExtraction(claims=[
                    ClaimToVerify(
                        statement="Revenue grew 25%.",
                        evidence_query="revenue growth",
                        calculation=CalculationCheck(
                            calculation_type="growth_rate",
                            inputs={"old_value": 100, "new_value": 120},
                            claimed_value=25,
                        ),
                    )
                ])
            self.verification_prompt = prompt
            return VerdictBundle(claims=[
                ClaimVerdict(
                    statement="Revenue grew 25%.",
                    status="verified",
                    rationale="The retrieved passage supports revenue growth.",
                    evidence="Revenue grew 20%.",
                )
            ])

        return SimpleNamespace(ainvoke=ainvoke)


@pytest.mark.asyncio
async def test_fact_checker_retrieves_fresh_evidence_and_overrides_bad_math(monkeypatch):
    import src.agents.fact_checker as fact_checker

    llm = StructuredFakeLLM()
    search_tool = FakeTool("search_financial_documents", "Revenue grew 20%.")
    monkeypatch.setattr(fact_checker, "ChatGoogleGenerativeAI", lambda **kwargs: llm)

    async def discover_tools():
        return [search_tool]

    monkeypatch.setattr(fact_checker, "get_mcp_tools", discover_tools)
    node = create_fact_checker_node()
    result = await node({
        "analysis": "Revenue grew 25%.",
        "ticker": "AAPL",
        "research_data": {"private_summary": "This must not be used as evidence."},
        "errors": [],
        "iteration_count": 1,
    })

    claim = result["fact_check_results"]["claims"][0]
    assert search_tool.calls == [{"query": "revenue growth", "num_results": 3}]
    assert claim["status"] == "contradicted"
    assert claim["calculation"]["calculated_value"] == pytest.approx(20)
    assert "private_summary" not in llm.verification_prompt
