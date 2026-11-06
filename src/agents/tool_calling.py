"""Helpers for executing model-requested tools in agent nodes."""
import json
import math
from collections.abc import Mapping
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool


def _json_safe(value: Any) -> Any:
    """Replace non-finite numeric values with null before JSON serialization."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    item = getattr(value, "item", None)
    if callable(item):
        try:
            scalar = item()
        except (TypeError, ValueError):
            pass
        else:
            if scalar is not value:
                return _json_safe(scalar)
    return value


def stringify_tool_result(result: Any) -> str:
    if isinstance(result, str):
        if result.lstrip().startswith(("{", "[")):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return result
        else:
            return result
    return json.dumps(
        _json_safe(result), default=str, allow_nan=False
    )


def stringify_model_content(content: Any) -> str:
    """Normalize text returned by chat models that emit content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            else:
                parts.append(
                    json.dumps(_json_safe(block), default=str, allow_nan=False)
                )
        return "\n".join(parts)
    return str(content)


async def invoke_with_tools(
    llm: BaseChatModel,
    tools: list[BaseTool],
    prompt: str,
    max_tool_rounds: int = 6,
) -> tuple[str, list[dict], list[str]]:
    """Run a bounded tool-calling loop and return its answer and tool evidence."""
    tools_by_name = {tool.name: tool for tool in tools}
    messages = [HumanMessage(content=prompt)]
    tool_results = []
    errors = []
    llm_with_tools = llm.bind_tools(tools)

    for _ in range(max_tool_rounds):
        response = await llm_with_tools.ainvoke(messages)
        # Keep the provider's assistant message intact; Gemini 3 tool calls carry
        # thought signatures that must be replayed with their tool results.
        messages.append(response)
        if not response.tool_calls:
            return stringify_tool_result(response.content), tool_results, errors

        for call in response.tool_calls:
            tool = tools_by_name.get(call["name"])
            if tool is None:
                error = f"Model requested unavailable tool: {call['name']}"
                errors.append(error)
                result = error
            else:
                try:
                    arguments = call.get("args") or {}
                    result = stringify_tool_result(
                        await tool.ainvoke(arguments)
                    )
                except Exception as exc:
                    error = f"{call['name']} failed: {exc}"
                    errors.append(error)
                    result = error

            tool_results.append({
                "name": call["name"],
                "arguments": call.get("args") or {},
                "result": result,
            })
            messages.append(
                ToolMessage(
                    content=result,
                    tool_call_id=call["id"],
                    name=call["name"],
                )
            )

    response = await llm.ainvoke(messages)
    if response.tool_calls:
        errors.append("Tool-call limit reached before the model completed its response.")
    return stringify_tool_result(response.content), tool_results, errors
