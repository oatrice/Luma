import os
import pytest
from unittest.mock import patch, MagicMock

def test_go_architect_execution():
    """
    Test the Go Architect Agent flow (Red -> Green).
    Verifies that the agent generates code and writes to a file.
    """
    # Verify main module exists
    try:
        import main
    except ImportError:
        pytest.fail("main.py does not exist yet (Expected RED state)")

    # Preparation for the test
    test_state = {
        "task": "Generate a test go file",
        "filename": "test_gen.go",
        "code_content": ""
    }
    
    mock_code = "package main\nfunc main() { print('test') }"

    # We mock ChatGoogleGenerativeAI to avoid real calls and costs during unit tests
    with patch('main.ChatGoogleGenerativeAI') as MockLLM:
        mock_instance = MockLLM.return_value
        mock_instance.invoke.return_value.content = mock_code
        
        # We mock TARGET_DIR to avoid cluttering the real directory during automated tests
        with patch('main.TARGET_DIR', 'tests/temp_out'):
            # Execute
            result = main.app.invoke(test_state)
            
            # Assertions
            assert result['code_content'] == mock_code
            
            expected_path = os.path.join('tests/temp_out', 'test_gen.go')
            assert os.path.exists(expected_path), f"File was not created at {expected_path}"
            
            # Verify content
            with open(expected_path, 'r') as f:
                content = f.read()
            assert content == mock_code
            
            # Cleanup
            os.remove(expected_path)
            os.rmdir('tests/temp_out')
