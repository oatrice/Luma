import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path to find luma_core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luma_core.config import TARGET_DIR
from luma_core.tools import update_android_version_logic
from luma_core.agents.coder import coder_agent
from luma_core.state import AgentState

def test_project_structure_imports():
    """Test that we can import all key modules from the refactored core"""
    try:
        import luma_core.config
        import luma_core.state
        import luma_core.workflow
        import luma_core.agents.coder
        import luma_core.agents.reviewer
        import luma_core.agents.publisher
    except ImportError as e:
        pytest.fail(f"Failed to import refactored modules: {e}")

def test_config_target_dir():
    """Test configuration loading"""
    assert TARGET_DIR is not None
    assert isinstance(TARGET_DIR, str)

@patch("luma_core.tools.subprocess.run")
@patch("luma_core.tools.get_llm")
def test_update_android_version_logic(mock_get_llm, mock_subprocess):
    """Test logic for Option 5 (Android Update) without actual side effects"""
    # Setup Mock LLM
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    mock_llm_instance.invoke.return_value.content = "- Fixed crash"
    
    # Setup Mock Subprocess
    # 1. bump script
    # 2. git log
    mock_subprocess.return_value.stdout = "feat: test commit"
    mock_subprocess.return_value.returncode = 0
    
    # Mock File IO to avoid writing to real CHANGELOG
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        # Mock file read content to contain the expected placeholder
        mock_file_handle = MagicMock()
        mock_file_handle.read.return_value = "## [1.2.3]\n### Fixed\n*\n\n### Added\n*\n"
        mock_open.return_value.__enter__.return_value = mock_file_handle
        
        with patch("os.path.exists", return_value=True):
            update_android_version_logic("1.2.3")
            
    # Verification
    # Check if bump_version.sh was called
    calls = mock_subprocess.call_args_list
    bump_called = False
    for call in calls:
        cmd = call[0][0] # The command list
        if "./scripts/bump_version.sh" in cmd and "1.2.3" in cmd:
            bump_called = True
            break
            
    assert bump_called, "bump_version.sh should be called with version 1.2.3"

@patch("luma_core.agents.coder.get_llm")
def test_coder_agent_structure(mock_get_llm):
    """Test that Coder Agent returns correct dictionary structure"""
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    
    # Simulate LLM returning XML code
    mock_llm_instance.invoke.return_value.content = '<file path="test.py">print("hello")</file>'
    
    state = AgentState(
        task="Write hello world",
        iterations=0,
        changes={},
        test_errors="",
        source_files=[]
    )
    
    result = coder_agent(state)
    
    assert "changes" in result
    assert "test.py" in result["changes"]
    assert result["changes"]["test.py"] == 'print("hello")'
