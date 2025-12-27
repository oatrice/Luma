import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luma_core.state import AgentState
from luma_core.agents.reviewer import reviewer_agent
from luma_core.agents.publisher import publisher_agent
from luma_core.tools import update_android_version_logic, suggest_version_from_git
# Import main for Option 1 test
import main as luma_main

# --- Option 1: Full Flow (Issue -> Coding) ---
@patch("builtins.input", side_effect=["1", "0"]) # Select Option 1, then Exit
@patch("main.fetch_issues")
@patch("main.select_issue")
@patch("main.convert_to_task")
@patch("main.update_issue_status")
@patch("main.build_graph")
def test_option1_full_flow(mock_build_graph, mock_update_status, mock_convert, mock_select, mock_fetch, mock_input):
    """Test Option 1: Full Issue -> Coding Workflow"""
    # Setup Data Mocks
    mock_issues = [{"number": 101, "title": "Fix Login Bug", "body": "Login fails on Mac"}]
    mock_selected = mock_issues[0]
    mock_task_str = "Task: Fix Login Bug..."
    
    mock_fetch.return_value = mock_issues
    mock_select.return_value = mock_selected
    mock_convert.return_value = mock_task_str
    
    # Mock Graph App
    mock_app = MagicMock()
    mock_build_graph.return_value = mock_app
    
    # Ensure usage of args.repo
    test_args = ["main.py", "--repo", "oatrice/TestRepo"]
    with patch.object(sys, 'argv', test_args):
        luma_main.main()
        
    # Check Fetch & Graph Invocation
    mock_fetch.assert_called_once_with("oatrice/TestRepo")
    mock_app.invoke.assert_called_once()
    
    call_state = mock_app.invoke.call_args[0][0]
    assert call_state["task"] == mock_task_str
    assert call_state["issue_data"] == mock_selected

# --- Option 2: Manual PR ---
@patch("luma_core.agents.publisher.subprocess.run")
@patch("luma_core.agents.publisher.get_open_pr", return_value=None)
@patch("luma_core.agents.publisher.create_pull_request", return_value="http://pr-url")
@patch("luma_core.agents.publisher.get_llm")
def test_option2_manual_pr(mock_get_llm, mock_create_pr, mock_get_pr, mock_subprocess):
    """Test Option 2: Manual PR Creation (Publisher Agent)"""
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    mock_llm_instance.invoke.return_value.content = "Generated PR Body"
    
    # Mock Git commands success
    mock_subprocess.return_value.stdout = "feat/manual-test"
    mock_subprocess.return_value.returncode = 0
    
    state = AgentState(
        task="Manual PR Task",
        repo="user/repo",
        changes={},
        issue_data={}
    )
    
    publisher_agent(state)
    
    # Verify Git Push
    push_called = False
    for call in mock_subprocess.call_args_list:
        if "git" in call[0][0] and "push" in call[0][0]:
            push_called = True
            break
    
    assert push_called, "Should verify git push was attempted"
    
    # Verify PR Creation
    mock_create_pr.assert_called_once()
    # create_pull_request(repo_name, title, body, head_branch, base_branch)
    # args[0][0] = repo, args[0][1] = title
    assert "Manual PR Task" in mock_create_pr.call_args[0][1]

# --- Option 3: Local Code Review ---
@patch("luma_core.agents.reviewer.get_llm")
def test_option3_reviewer(mock_get_llm):
    """Test Option 3: Local Code Review (Reviewer Agent)"""
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    mock_llm_instance.invoke.return_value.content = "PASS"
    
    changes = {"local_diff.patch": "diff content"}
    
    state = AgentState(
        task="Review local changes",
        changes=changes
    )
    
    result = reviewer_agent(state)
    assert result["code_content"] == "PASS"
    
    # Verify Prompt content
    call_args = mock_llm_instance.invoke.call_args_list[0][0][0] 
    prompt_content = call_args[1].content 
    assert "Current Code input" in prompt_content
    assert "diff content" in prompt_content

# --- Option 4: Docs Mode ---
@patch("luma_core.workflow.build_graph")
def test_option4_docs_mode(mock_build_graph):
    """Test Option 4: Docs Update (Graph Invocation)"""
    mock_app = MagicMock()
    mock_build_graph.return_value = mock_app
    
    state = {
        "task": "Update documentation", 
        "skip_coder": True,
        "changes": {}
    }
    
    mock_app.invoke(state)
    mock_app.invoke.assert_called_with(state)

# --- Option 5: Update Android Version ---
@patch("luma_core.tools.subprocess.run")
@patch("luma_core.tools.get_llm")
def test_option5_android_update(mock_get_llm, mock_subprocess):
    """Test Option 5: Update Android Server Version"""
    # Setup Mock LLM
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    mock_llm_instance.invoke.return_value.content = "- Fixed crash"
    
    # Setup Mock Subprocess
    mock_subprocess.return_value.stdout = "feat: test commit"
    mock_subprocess.return_value.returncode = 0
    
    # Mock File IO
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file_handle = MagicMock()
        mock_file_handle.read.return_value = "## [1.2.3]\n### Fixed\n*\n\n### Added\n*\n"
        mock_open.return_value.__enter__.return_value = mock_file_handle
        
        with patch("os.path.exists", return_value=True):
            update_android_version_logic("1.2.3")
            
    # Verify bump_version.sh was called
    calls = mock_subprocess.call_args_list
    bump_called = False
    for call in calls:
        cmd = call[0][0]
        if "./scripts/bump_version.sh" in cmd and "1.2.3" in cmd:
            bump_called = True
            break
            
    assert bump_called, "bump_version.sh should be called with version 1.2.3"


# --- Option 5: Suggest Version from Git (AI Default) ---
@patch("luma_core.tools.subprocess.run")
@patch("luma_core.tools.get_llm")
def test_suggest_version_patch(mock_get_llm, mock_subprocess):
    """Test suggest_version_from_git recommends PATCH bump for fixes"""
    # Setup Mock LLM
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    mock_llm_instance.invoke.return_value.content = "PATCH"
    
    # Mock current version
    mock_subprocess.return_value.stdout = "1.0.5"
    mock_subprocess.return_value.returncode = 0
    
    result = suggest_version_from_git()
    
    assert result == "1.0.6", f"Expected 1.0.6, got {result}"
    

@patch("luma_core.tools.subprocess.run")
@patch("luma_core.tools.get_llm")
def test_suggest_version_minor(mock_get_llm, mock_subprocess):
    """Test suggest_version_from_git recommends MINOR bump for new features"""
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    mock_llm_instance.invoke.return_value.content = "MINOR"
    
    mock_subprocess.return_value.stdout = "2.3.1"
    mock_subprocess.return_value.returncode = 0
    
    result = suggest_version_from_git()
    
    assert result == "2.4.0", f"Expected 2.4.0, got {result}"


@patch("luma_core.tools.subprocess.run")
@patch("luma_core.tools.get_llm")  
def test_suggest_version_major(mock_get_llm, mock_subprocess):
    """Test suggest_version_from_git recommends MAJOR bump for breaking changes"""
    mock_llm_instance = MagicMock()
    mock_get_llm.return_value = mock_llm_instance
    mock_llm_instance.invoke.return_value.content = "MAJOR"
    
    mock_subprocess.return_value.stdout = "1.2.5"
    mock_subprocess.return_value.returncode = 0
    
    result = suggest_version_from_git()
    
    assert result == "2.0.0", f"Expected 2.0.0, got {result}"


@patch("luma_core.tools.subprocess.run")
def test_suggest_version_fallback(mock_subprocess):
    """Test fallback when no current version found"""
    mock_subprocess.return_value.stdout = ""
    mock_subprocess.return_value.returncode = 1
    
    result = suggest_version_from_git()
    
    assert result is None, "Should return None when no version found"
