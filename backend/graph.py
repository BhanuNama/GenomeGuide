"""
LangGraph State Machine — GenomeGuide Pipeline
Wires all 5 agents into a directed graph with a conditional retry edge.

Graph topology:
  START
    → parser_node
    → lookup_node
    → classifier_node
    → explainer_node
    → critic_node  ──(passed)──→ END
                   ──(retry)──→ explainer_node  (max 2 retries)
"""
from langgraph.graph import StateGraph, END
from state import GenomeGuideState
from agents.parser_agent import parser_node
from agents.lookup_agent import lookup_node
from agents.classifier_agent import classifier_node
from agents.explainer_agent import explainer_node
from agents.critic_agent import critic_node, should_retry


def build_graph():
    """Build and compile the LangGraph pipeline."""
    workflow = StateGraph(GenomeGuideState)

    # Register all nodes
    workflow.add_node("parser",     parser_node)
    workflow.add_node("lookup",     lookup_node)
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("explainer",  explainer_node)
    workflow.add_node("critic",     critic_node)

    # Linear edges
    workflow.set_entry_point("parser")
    workflow.add_edge("parser",     "lookup")
    workflow.add_edge("lookup",     "classifier")
    workflow.add_edge("classifier", "explainer")
    workflow.add_edge("explainer",  "critic")

    # Conditional edge: critic → retry explainer OR end
    workflow.add_conditional_edges(
        "critic",
        should_retry,
        {
            "retry": "explainer",   # re-run explainer with critic feedback in state
            "end":   END,
        }
    )

    return workflow.compile()


# Singleton compiled graph
graph = build_graph()
