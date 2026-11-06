"""LangGraph conversation memory for questions about generated reports."""
from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.agents.tool_calling import stringify_model_content


class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def build_conversation_graph(llm: BaseChatModel, checkpointer=None):
    """Build a conversation graph whose message history is checkpointed by thread."""
    async def answer_question(state: ConversationState) -> dict:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}

    workflow = StateGraph(ConversationState)
    workflow.add_node("answer", answer_question)
    workflow.set_entry_point("answer")
    workflow.add_edge("answer", END)
    return workflow.compile(
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver()
    )


conversation_graph = build_conversation_graph(
    ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.2,
    )
)


async def start_report_conversation(report: str, citations: list[dict]) -> str:
    """Create a conversation thread seeded with its report and sources."""
    conversation_id = str(uuid4())
    citations_text = "\n".join(
        f"- [{citation.get('id', '?')}] {citation.get('source_name', 'Unknown')}: "
        f"{citation.get('excerpt', '')}"
        for citation in citations
    )
    context = (
        "Answer follow-up questions about the financial research report below. "
        "Use the report and its sources as context. Do not invent facts; if the "
        "report does not contain enough information, say so. Distinguish report "
        "statements from any general explanation.\n\n"
        f"Research report:\n{report}\n\n"
        f"Sources:\n{citations_text or 'No source list was returned.'}"
    )
    await conversation_graph.aupdate_state(
        {"configurable": {"thread_id": conversation_id}},
        {"messages": [SystemMessage(content=context)]},
    )
    return conversation_id


async def ask_follow_up(conversation_id: str, question: str) -> str:
    """Ask a question in an existing report conversation and retain the turn."""
    config = {"configurable": {"thread_id": conversation_id}}
    checkpoint = await conversation_graph.aget_state(config)
    if not checkpoint.values.get("messages"):
        raise LookupError("Conversation not found or expired.")

    result = await conversation_graph.ainvoke(
        {"messages": [HumanMessage(content=question)]},
        config=config,
    )
    return stringify_model_content(result["messages"][-1].content)
