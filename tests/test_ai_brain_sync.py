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

# --- get_latest_session ---

def test_get_latest_session(mock_brain_dir):
    latest_path = AntigravityBrain.get_latest_session()
    assert latest_path is not None
    assert "2466c0f9-3333" in latest_path

# --- get_all_sessions ---

def test_get_all_sessions_returns_sorted_list(mock_brain_dir):
    """Should return all valid sessions sorted by mtime (newest first)."""
    sessions = AntigravityBrain.get_all_sessions()
    assert len(sessions) == 2  # Only 2 have task.md
    # Newest first
    assert "2466c0f9-3333" in sessions[0]["path"]
    assert "2466c0f9-1111" in sessions[1]["path"]

def test_get_all_sessions_includes_preview(mock_brain_dir):
    """Each session should include a preview (first line of task.md)."""
    sessions = AntigravityBrain.get_all_sessions()
    assert sessions[0]["preview"] == "# Active Task Number 45"
    assert sessions[1]["preview"] == "# Old Issue"

def test_get_all_sessions_includes_session_id(mock_brain_dir):
    """Each session has a short session_id from the dir name."""
    sessions = AntigravityBrain.get_all_sessions()
    assert sessions[0]["session_id"] == "2466c0f9-3333"

# --- sync_to_repo with explicit session_path ---

def test_sync_to_repo_creates_in_features_dir(mock_brain_dir, tmp_path):
    """sync_to_repo should create ai_brain/ inside docs/features/{N}_issue-{N}/"""
    project_dir = str(tmp_path / "repo")
    os.makedirs(project_dir)
    
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 45)
    
    assert len(synced_files) == 2
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "implementation_plan.md"))
    
    assert os.path.join("docs", "features", "45_issue-45", "ai_brain", "task.md") in synced_files
    assert os.path.join("docs", "features", "45_issue-45", "ai_brain", "implementation_plan.md") in synced_files

def test_sync_to_repo_uses_existing_feature_dir(mock_brain_dir, tmp_path):
    """When a feature dir already exists, sync into it."""
    project_dir = str(tmp_path / "repo2")
    os.makedirs(project_dir)
    
    existing_dir = os.path.join(project_dir, "docs", "features", "5_issue-45_cool-feature")
    os.makedirs(existing_dir)
    
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 45)
    
    assert len(synced_files) == 2
    
    target_dir = os.path.join(existing_dir, "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "implementation_plan.md"))

def test_sync_to_repo_with_explicit_session(mock_brain_dir, tmp_path):
    """Should use the explicit session_path instead of auto-detecting latest."""
    project_dir = str(tmp_path / "repo_explicit")
    os.makedirs(project_dir)
    
    # Pick the OLD session explicitly (not the latest)
    old_session = os.path.join(mock_brain_dir, "2466c0f9-1111")
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 99, session_path=old_session)
    
    assert len(synced_files) == 1  # Only task.md exists in old session
    
    target_dir = os.path.join(project_dir, "docs", "features", "99_issue-99", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    
    # Verify it's the OLD content
    with open(os.path.join(target_dir, "task.md")) as f:
        assert "Old Issue" in f.read()

# --- Versioning ---

def test_sync_versioning_same_content_skips(mock_brain_dir, tmp_path):
    """If file content is identical, don't create a new version."""
    project_dir = str(tmp_path / "repo_ver1")
    os.makedirs(project_dir)
    
    synced1 = AntigravityBrain.sync_to_repo(project_dir, 45)
    assert len(synced1) == 2
    
    synced2 = AntigravityBrain.sync_to_repo(project_dir, 45)
    assert len(synced2) == 0
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    assert not os.path.exists(os.path.join(target_dir, "task_v2.md"))

def test_sync_versioning_different_content_creates_v2(mock_brain_dir, tmp_path):
    """If file content changed, save as _v2."""
    project_dir = str(tmp_path / "repo_ver2")
    os.makedirs(project_dir)
    
    synced1 = AntigravityBrain.sync_to_repo(project_dir, 45)
    assert len(synced1) == 2
    
    sess3 = os.path.join(mock_brain_dir, "2466c0f9-3333")
    with open(os.path.join(sess3, "task.md"), "w") as f:
        f.write("# Updated Task v2")
    
    synced2 = AntigravityBrain.sync_to_repo(project_dir, 45)
    assert len(synced2) >= 1
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "task_v2.md"))
    
    with open(os.path.join(target_dir, "task_v2.md")) as f:
        assert "Updated Task v2" in f.read()

def test_sync_versioning_v3(mock_brain_dir, tmp_path):
    """Third sync with different content creates _v3."""
    project_dir = str(tmp_path / "repo_ver3")
    os.makedirs(project_dir)
    
    sess3 = os.path.join(mock_brain_dir, "2466c0f9-3333")
    
    AntigravityBrain.sync_to_repo(project_dir, 45)
    
    with open(os.path.join(sess3, "task.md"), "w") as f:
        f.write("# Task v2")
    AntigravityBrain.sync_to_repo(project_dir, 45)
    
    with open(os.path.join(sess3, "task.md"), "w") as f:
        f.write("# Task v3")
    AntigravityBrain.sync_to_repo(project_dir, 45)
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "task_v2.md"))
    assert os.path.exists(os.path.join(target_dir, "task_v3.md"))
    
    with open(os.path.join(target_dir, "task_v3.md")) as f:
        assert "Task v3" in f.read()

# --- Integration with action ---

def test_action_sync_ai_brain_logic(mock_brain_dir, tmp_path, monkeypatch):
    import os
    from luma_core.state_manager import LumaState, IssueData
    from luma_core.actions import action_sync_ai_brain
    
    project_dir = str(tmp_path / "repo3")
    os.makedirs(project_dir)
    
    import subprocess
    class MockCompletedProcess:
        returncode = 0
        stdout = ""
        stderr = ""
        
    def mock_subprocess_run(*args, **kwargs):
        return MockCompletedProcess()
        
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    # Auto-confirm preview
    monkeypatch.setattr("builtins.input", lambda _: "y")
    
    state = LumaState(project_key="1")
    state.active_issue = IssueData(
        number=45, title="Test", html_url="", body="", project_item_id="", project_id="", repository=""
    )
    
    project = {
        "name": "Test Project",
        "path": project_dir,
        "repo": "test/test"
    }
    
    result = action_sync_ai_brain(state, project)
    assert result is True
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
