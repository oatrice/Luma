from langgraph.graph import StateGraph, END
from .state import AgentState

# Import Agents
from .agents.coder import coder_agent
from .agents.reviewer import reviewer_agent, docs_reviewer_agent
from .agents.tester import tester_agent, should_continue
from .agents.docs import docs_agent
from .agents.publisher import publisher_agent
from .agents.common import human_approval_agent, approval_gate, file_writer

def build_graph():
    """Constructs the Agent Workflow Graph"""
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("Coder", coder_agent)
    workflow.add_node("Reviewer", reviewer_agent)
    workflow.add_node("Tester", tester_agent)
    workflow.add_node("Docs", docs_agent)
    workflow.add_node("Approver", human_approval_agent)
    workflow.add_node("Writer", file_writer)
    workflow.add_node("Publisher", publisher_agent)
    workflow.add_node("DocsReviewer", docs_reviewer_agent)
    
    # Define Flow
    workflow.set_entry_point("Coder")
    workflow.add_edge("Coder", "Reviewer")
    workflow.add_edge("Reviewer", "Tester")
    
    # Tester Loops back to Coder if failed
    workflow.add_conditional_edges(
        "Tester",
        should_continue,
        {
            "retry": "Coder",
            "pass": "Docs"
        }
    )
    
    workflow.add_edge("Docs", "DocsReviewer")
    workflow.add_edge("DocsReviewer", "Approver")

    
    # Approval Gate
    workflow.add_conditional_edges(
        "Approver",
        approval_gate,
        {
            "yes": "Writer",
            "no": END
        }
    )
    
    workflow.add_edge("Writer", "Publisher")
    workflow.add_edge("Publisher", END)
    
    return workflow.compile()
