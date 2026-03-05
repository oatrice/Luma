import os
import shutil
import pytest
from luma_core.ai_brain_sync import AntigravityBrain

@pytest.fixture
def mock_brain_dir(tmp_path, monkeypatch):
    """Setup mock brain directory with multiple fake sessions."""
    brain_root = tmp_path / "brain"
    brain_root.mkdir()
    
    # Session 1: Oldest
    sess1 = brain_root / "2466c0f9-1111"
    sess1.mkdir()
    (sess1 / "task.md").write_text("# Old Issue")
    os.utime(sess1, (500000000, 500000000))
    
    # Session 2: Newest, but empty (no task.md)
    sess2 = brain_root / "2466c0f9-2222"
    sess2.mkdir()
    os.utime(sess2, (1700000000, 1700000000))
    
    # Session 3: Recent with required files
    sess3 = brain_root / "2466c0f9-3333"
    sess3.mkdir()
    (sess3 / "task.md").write_text("# Active Task Number 45")
    (sess3 / "implementation_plan.md").write_text("Plan")
    os.utime(sess3, (1600000000, 1600000000))

    monkeypatch.setattr(AntigravityBrain, "DEFAULT_BRAIN_PATH", str(brain_root))
    return str(brain_root)

def test_get_latest_session(mock_brain_dir):
    # Expect to find Session 3 because it has 'task.md', even if Session 2 is newer
    latest_path = AntigravityBrain.get_latest_session()
    assert latest_path is not None
    assert "2466c0f9-3333" in latest_path

def test_sync_to_repo(mock_brain_dir, tmp_path):
    project_dir = str(tmp_path / "repo")
    os.makedirs(project_dir)
    
    # Run sync
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 45)
    
    # Expect 2 files: task.md and implementation_plan.md (walkthrough.md does not exist in mock)
    assert len(synced_files) == 2
    
    target_dir = os.path.join(project_dir, "docs", "ai_brain", "issue-45")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "implementation_plan.md"))
    
    # Check returned relative paths
    assert os.path.join("docs", "ai_brain", "issue-45", "task.md") in synced_files
    assert os.path.join("docs", "ai_brain", "issue-45", "implementation_plan.md") in synced_files

def test_action_sync_ai_brain_logic(mock_brain_dir, tmp_path, monkeypatch):
    import os
    from luma_core.state_manager import LumaState, IssueData
    from luma_core.actions import action_sync_ai_brain
    
    project_dir = str(tmp_path / "repo2")
    os.makedirs(project_dir)
    
    import subprocess
    class MockCompletedProcess:
        returncode = 0
        stdout = ""
        stderr = ""
        
    def mock_subprocess_run(*args, **kwargs):
        return MockCompletedProcess()
        
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    
    state = LumaState(project_key="1")
    state.active_issue = IssueData(
        number=45, title="Test", html_url="", body="", project_item_id="", project_id="", repository=""
    )
    
    project = {
        "name": "Test Project",
        "path": project_dir,
        "repo": "test/test"
    }
    
    # Action should return True on success
    result = action_sync_ai_brain(state, project)
    assert result is True
    
    # Assert side effects
    target_dir = os.path.join(project_dir, "docs", "ai_brain", "issue-45")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
