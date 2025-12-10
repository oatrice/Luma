
import os
import pytest
from unittest.mock import patch, MagicMock
import main
import shutil

# Helper to mockup subprocess run
def mock_subprocess_run(*args, **kwargs):
    # Mock return pass (returncode=0)
    return MagicMock(returncode=0, stdout="PASS", stderr="")

def test_tester_reverts_changes_logic():
    """
    Tester Agent should:
    1. Backup existing file
    2. Write new draft
    3. Run Test
    4. Revert to backup (Verify file on disk is ORIGINAL, not DRAFT)
    """
    if not hasattr(main, 'tester_agent'):
         pytest.fail("tester_agent not implemented")
         
    filename = "temp_server_test.go" # Use a temp name to avoid messing with real server.go in 'tests'
    # Actually main.TARGET_DIR points to ../Tetris-Battle. 
    # For safety in test, let's mock TARGET_DIR locally if possible, 
    # but strictly following the plan, let's just use patch to redirect file ops?
    # No, integration test style is better. Let's use a unique filename.
    
    original_content = "package main\n// Original Safe Code"
    draft_content = "package main\n// New Draft Code"
    
    # Path Setup - We temporarily override TARGET_DIR for safety if possible, or just be careful.
    # Assuming main.TARGET_DIR is "../Tetris-Battle".
    # Let's create a temporary directory for this test
    temp_test_dir = "./tests/temp_workspace"
    full_path = os.path.join(temp_test_dir, filename)
    
    os.makedirs(temp_test_dir, exist_ok=True)
    
    # Create "Original" file
    with open(full_path, "w") as f:
        f.write(original_content)
        
    state = {
        "task": "Update server",
        "code_content": draft_content,
        "filename": filename
    }
    
    # Patch TARGET_DIR in main module dynamically
    with patch('main.TARGET_DIR', temp_test_dir):
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            # Run Tester Agent
            main.tester_agent(state)
            
    # Validation: Content on disk MUST be ORIGINAL (Tester should only touch it transiently)
    if not os.path.exists(full_path):
         pytest.fail("File disappeared!")
         
    with open(full_path, "r") as f:
        current_content = f.read()
        
    # Cleanup first
    if os.path.exists(temp_test_dir): shutil.rmtree(temp_test_dir)
    
    # Assert
    assert current_content == original_content, \
        f"Tester failed to revert changes!\nExpected: {original_content}\nGot: {current_content}"
