# src/agents/state.py
"""
LangGraph state definitions for the research workflow.
"""
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ResearchState(TypedDict):
    """State that flows through the research agent graph."""

    # The user's research query
    query: str

    # The company/ticker being researched
    ticker: str

    # Messages for the agent conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Research data collected by the researcher
    research_data: dict

    # Analysis produced by the analyst
    analysis: str

    # Fact-check results
    fact_check_results: dict

    # Final report
    final_report: str

    # Citations collected during research
    citations: list[dict]

    # Current phase of the workflow
    current_phase: str

    # Number of research iterations
    iteration_count: int

    # Whether the research needs more data
    needs_more_research: bool

    # Error tracking
    errors: list[str]