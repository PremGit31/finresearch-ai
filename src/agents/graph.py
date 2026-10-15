# src/agents/graph.py
"""
LangGraph workflow orchestration — connects researcher, analyst, fact-checker, and report writer.
"""
from langgraph.graph import StateGraph, END

from src.agents.state import ResearchState
from src.agents.researcher import create_researcher_node
from src.agents.analyst import create_analyst_node
from src.agents.fact_checker import create_fact_checker_node
from src.agents.report_writer import create_report_writer_node
from config.settings import MAX_RESEARCH_ITERATIONS


def should_continue_research(state: ResearchState) -> str:
    """Decide whether to loop back for more research or proceed to report writing."""
    if (
        state.get("needs_more_research", False)
        and state.get("iteration_count", 0) < MAX_RESEARCH_ITERATIONS
    ):
        return "researcher"
    return "report_writer"


def build_research_graph() -> StateGraph:
    """Build the LangGraph research workflow.

    Flow:
        researcher → analyst → fact_checker → (loop back or report_writer) → END
    """
    workflow = StateGraph(ResearchState)

    # Create node functions
    researcher = create_researcher_node()
    analyst = create_analyst_node()
    fact_checker = create_fact_checker_node()
    report_writer = create_report_writer_node()

    # Add nodes
    workflow.add_node("researcher", researcher)
    workflow.add_node("analyst", analyst)
    workflow.add_node("fact_checker", fact_checker)
    workflow.add_node("report_writer", report_writer)

    # Define edges
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "fact_checker")

    # Conditional edge: fact_checker decides whether to loop or finish
    workflow.add_conditional_edges(
        "fact_checker",
        should_continue_research,
        {
            "researcher": "researcher",
            "report_writer": "report_writer",
        },
    )

    workflow.add_edge("report_writer", END)

    return workflow.compile()


# Pre-built graph instance
research_graph = build_research_graph()