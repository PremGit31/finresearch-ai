import json

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from src.agents.conversation import build_conversation_graph
from src.utils.helpers import escape_currency_for_markdown


class ContextualFakeLLM:
    def __init__(self):
        self.message_history = []

    async def ainvoke(self, messages):
        self.message_history.append(list(messages))
        question_count = sum(
            message.type == "human" for message in messages
        )
        return AIMessage(content=f"Answer {question_count}")


@pytest.mark.asyncio
async def test_conversation_graph_retains_report_context_and_follow_up_turns():
    llm = ContextualFakeLLM()
    graph = build_conversation_graph(llm, InMemorySaver())
    config = {"configurable": {"thread_id": "report-1"}}
    await graph.aupdate_state(
        config,
        {"messages": [{"role": "system", "content": "Report context"}]},
    )

    first = await graph.ainvoke(
        {"messages": [{"role": "human", "content": "What was revenue?"}]},
        config=config,
    )
    second = await graph.ainvoke(
        {"messages": [{"role": "human", "content": "And net income?"}]},
        config=config,
    )

    assert first["messages"][-1].content == "Answer 1"
    assert second["messages"][-1].content == "Answer 2"
    assert llm.message_history[1][0].content == "Report context"
    assert [message.type for message in llm.message_history[1]] == [
        "system", "human", "ai", "human",
    ]


@pytest.mark.asyncio
async def test_report_conversation_is_seeded_and_unknown_threads_are_rejected(monkeypatch):
    import src.agents.conversation as conversation

    graph = build_conversation_graph(ContextualFakeLLM(), InMemorySaver())
    monkeypatch.setattr(conversation, "conversation_graph", graph)

    conversation_id = await conversation.start_report_conversation(
        "Revenue was $20 billion.", [{"id": "[1]", "source_name": "10-K"}]
    )
    checkpoint = await graph.aget_state({
        "configurable": {"thread_id": conversation_id}
    })

    assert "Revenue was $20 billion." in checkpoint.values["messages"][0].content
    assert "10-K" in checkpoint.values["messages"][0].content
    answer = await conversation.ask_follow_up(
        conversation_id, "What was revenue?"
    )
    assert answer == "Answer 1"
    with pytest.raises(LookupError, match="not found or expired"):
        await conversation.ask_follow_up("unknown-thread", "Question")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Revenue was $20.25 billion.", r"Revenue was \$20.25 billion."),
        ("Income: $ 11.43 billion.", r"Income: \$ 11.43 billion."),
        ("Use $x$ for a variable.", "Use $x$ for a variable."),
        (r"Already escaped: \$10.", r"Already escaped: \$10."),
    ],
)
def test_currency_amounts_do_not_become_inline_math(text, expected):
    assert escape_currency_for_markdown(text) == expected


def test_currency_display_fix_leaves_downloaded_report_unchanged():
    report = "Revenue was $20.25 billion."

    display_text = escape_currency_for_markdown(report)
    exported_text = json.dumps({"report": report})

    assert r"\$20.25" in display_text
    assert "$20.25" in json.loads(exported_text)["report"]
