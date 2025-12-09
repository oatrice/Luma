
import pytest
from unittest.mock import patch
import main

def test_reviewer_node_exists():
    """
    Test that the Reviewer node is defined and integrated into the workflow.
    """
    # ตรวจสอบว่ามีฟังก์ชัน reviewer_agent
    assert hasattr(main, 'reviewer_agent'), "reviewer_agent function should exist in main.py"
    
    # ตรวจสอบว่ามี Node ชื่อ 'Reviewer' อยู่ใน Graph
    # หมายเหตุ: การเข้าถึง nodes ใน LangGraph อาจแตกต่างกันไปตามเวอร์ชัน
    # วิธีนี้เป็นการตรวจสอบเบื้องต้น
    graph = main.app.get_graph()
    # graph.nodes return dictionary or list of nodes
    node_keys = [node for node in graph.nodes]
    assert 'Reviewer' in node_keys, "Reviewer node should be in the compiled graph"

def test_reviewer_logic():
    """
    Test logic of reviewer agent specifically
    """
    if not hasattr(main, 'reviewer_agent'):
        pytest.fail("reviewer_agent not implemented yet")

    state = {
        "task": "Write simple go code",
        "code_content": "package main\nfunc main() {}",
        "filename": "main.go"
    }
    
    with patch('main.ChatGoogleGenerativeAI') as MockLLM:
        mock_instance = MockLLM.return_value
        mock_instance.invoke.return_value.content = "package main\n// Reviewed\nfunc main() {}"
        
        # Test direct function call
        result = main.reviewer_agent(state)
        assert "Reviewed" in result['code_content']
