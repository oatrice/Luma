
import pytest
import main
from unittest.mock import patch, MagicMock

def test_architect_plan_structure():
    """Verify State supports multi-file changes"""
    # Check if 'changes' field exists in TypedDict (by checking annotations)
    # AgentState is a TypedDict, we can inspect its __annotations__
    assert 'changes' in main.AgentState.__annotations__, "AgentState must support 'changes' dict for multi-file"

def test_writer_handles_multiple_files():
    """Writer should be able to iterate over 'changes' and write all of them"""
    if not hasattr(main, 'file_writer'):
        pytest.fail("Writer not implemented")
        
    state = {
        "task": "Test Save",
        "filename": "dummy", # Legacy field support
        "code_content": "",
        "changes": {
            "file1.go": "content1", 
            "file2.go": "content2"
        }
    }
    
    # Mock open/makedirs
    # We want to verify that open() is called twice with correct paths
    with patch('builtins.open', MagicMock()) as mock_open:
        with patch('os.makedirs'):
             main.file_writer(state)
             
    # Assertions
    # Check that open was called for file1 and file2
    # mock_open call args format: open(file, mode, ...)
    # Get all 'file' arguments passed to open
    called_paths = []
    for call in mock_open.call_args_list:
        args, _ = call
        called_paths.append(str(args[0]))
        
    print(f"Called paths: {called_paths}")
        
    assert any("file1.go" in path for path in called_paths), "Writer did not save file1.go"
    assert any("file2.go" in path for path in called_paths), "Writer did not save file2.go"
