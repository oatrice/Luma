
import pytest
from unittest.mock import patch
import main

def test_approval_flow_structure():
    """Check if Approver node exists in the graph"""
    graph = main.app.get_graph()
    # Note: Depending on Langgraph version, accessing nodes might differ.
    # We assume .nodes works as per previous tests.
    nodes = list(graph.nodes.keys())
    assert "Approver" in nodes, "Graph must contain an 'Approver' node"

@patch('builtins.input', return_value='y')
def test_approver_accepts(mock_input):
    """Test that 'y' input results in approval"""
    if not hasattr(main, 'human_approval_agent'):
        pytest.fail("human_approval_agent function not implemented")
    
    state = {"task": "test", "code_content": "foo", "filename": "bar"}
    # call function directly
    result = main.human_approval_agent(state)
    assert result.get("approved") is True

@patch('builtins.input', return_value='n')
def test_approver_rejects(mock_input):
    """Test that 'n' input results in rejection"""
    if not hasattr(main, 'human_approval_agent'):
        pytest.fail("human_approval_agent function not implemented")
        
    state = {"task": "test", "code_content": "foo", "filename": "bar"}
    result = main.human_approval_agent(state)
    assert result.get("approved") is False
