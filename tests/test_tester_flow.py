
import pytest
from unittest.mock import MagicMock, patch
import main

def test_tester_node_structure():
    """
    Test that the Tester node is integrated into the workflow:
    Reviewer -> Tester -> Writer
    """
    # 1. Check function existence
    assert hasattr(main, 'tester_agent'), "tester_agent function must exist"
    
    # 2. Check Graph Nodes
    graph = main.app.get_graph()
    # Note: Accessing nodes differently depending on langgraph version, 
    # but generally .nodes returns a dictionary-like object
    node_keys = list(graph.nodes.keys())
    assert 'Tester' in node_keys, "Tester node must be in the graph"

@patch('subprocess.run')
def test_tester_execution(mock_subprocess):
    """
    Test that tester_agent attempts to run go tests.
    """
    if not hasattr(main, 'tester_agent'):
        pytest.fail("tester_agent not implemented")

    state = {
        "task": "Update server",
        "code_content": "package main\nfunc main(){}",
        "filename": "server.go"
    }

    # Simulate success
    mock_subprocess.return_value = MagicMock(returncode=0, stdout=b"PASS", stderr=b"")

    # We mock file operations so we don't write garbage during unit test
    with patch('builtins.open', MagicMock()):
        with patch('os.path.exists', return_value=False): # Assume temp file doesn't exist yet
            main.tester_agent(state)

    # Verify subprocess called "go test"
    assert mock_subprocess.called
    args, _ = mock_subprocess.call_args
    # args[0] is typically the command list, e.g. ['go', 'test', './...']
    cmd_list = args[0]
    assert cmd_list[0] == "go" and cmd_list[1] == "test"
