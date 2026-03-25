import os
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
    
    # Session 3: Recent with required files + images
    sess3 = brain_root / "2466c0f9-3333"
    sess3.mkdir()
    
    # Contains absolute paths to images that should be replaced
    walkthrough_content = f"""# Walkthrough
    
![img1]({sess3}/screenshot_1234.png)
<img src="{sess3}/walkthrough_img.jpg" />
[link to task](file://{sess3}/task.md)
    """
    
    (sess3 / "task.md").write_text("# Active Task Number 45")
    (sess3 / "walkthrough.md").write_text(walkthrough_content)
    (sess3 / "screenshot_1234.png").write_bytes(b"\x89PNG fake image v1")
    (sess3 / "walkthrough_img.jpg").write_bytes(b"\xff\xd8 fake jpg")
    # File to skip
    (sess3 / ".resolve.3a947561-ec74.tmp").write_text("skip me too")
    # Hidden file (should be skipped)
    (sess3 / ".system_cache").write_text("skip me")
    # Metadata and resolved files (should be skipped)
    (sess3 / "walkthrough.md.metadata.json").write_text('{"key": "value"}')
    (sess3 / "walkthrough.md.resolved").write_text("resolved content")
    (sess3 / "walkthrough.md.resolved.0").write_text("resolved v0")
    (sess3 / "walkthrough.md.resolved.1").write_text("resolved v1")
    # Subdirectory (should be skipped)
    sub = sess3 / ".system_generated"
    sub.mkdir()
    (sub / "logs.txt").write_text("log data")
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
    sessions = AntigravityBrain.get_all_sessions()
    assert len(sessions) == 2
    assert "2466c0f9-3333" in sessions[0]["path"]
    assert "2466c0f9-1111" in sessions[1]["path"]

def test_get_all_sessions_includes_preview(mock_brain_dir):
    sessions = AntigravityBrain.get_all_sessions()
    assert sessions[0]["preview"] == "# Active Task Number 45"
    assert sessions[1]["preview"] == "# Old Issue"

def test_get_all_sessions_includes_session_id(mock_brain_dir):
    sessions = AntigravityBrain.get_all_sessions()
    assert sessions[0]["session_id"] == "2466c0f9-3333"

# --- sync all files ---

def test_sync_includes_images_but_skips_resolve(mock_brain_dir, tmp_path):
    """sync_to_repo should include image files, skip .resolve.* and hidden files."""
    project_dir = str(tmp_path / "repo")
    os.makedirs(project_dir)
    
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 45)
    
    # Should sync: task.md, walkthrough.md, screenshot_1234.png, walkthrough_img.jpg
    # Should NOT sync: .system_cache, .system_generated/, .resolve.*, *.metadata.json, *.resolved, *.resolved.N
    assert len(synced_files) == 4
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "walkthrough.md"))
    assert os.path.exists(os.path.join(target_dir, "screenshot_1234.png"))
    assert os.path.exists(os.path.join(target_dir, "walkthrough_img.jpg"))
    
    # Hidden files, dirs, .resolve.*, .metadata.json, .resolved should NOT be synced
    assert not os.path.exists(os.path.join(target_dir, ".system_cache"))
    assert not os.path.exists(os.path.join(target_dir, ".system_generated"))
    assert not list(filter(lambda x: x.startswith(".resolve."), os.listdir(target_dir)))

def test_sync_skips_metadata_and_resolved_files(mock_brain_dir, tmp_path):
    """sync_to_repo should skip .metadata.json, .resolved, and .resolved.N files."""
    project_dir = str(tmp_path / "repo_meta")
    os.makedirs(project_dir)
    
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 45)
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    
    # These artifact metadata files should NOT be synced
    assert not os.path.exists(os.path.join(target_dir, "walkthrough.md.metadata.json"))
    assert not os.path.exists(os.path.join(target_dir, "walkthrough.md.resolved"))
    assert not os.path.exists(os.path.join(target_dir, "walkthrough.md.resolved.0"))
    assert not os.path.exists(os.path.join(target_dir, "walkthrough.md.resolved.1"))
    
    # None of the synced file names should contain these suffixes
    for f in synced_files:
        assert ".metadata.json" not in f
        assert ".resolved" not in f

def test_sync_updates_image_paths_in_md(mock_brain_dir, tmp_path):
    """sync_to_repo should replace absolute brain session paths with relative paths in .md files."""
    project_dir = str(tmp_path / "repo_paths")
    os.makedirs(project_dir)
    
    AntigravityBrain.sync_to_repo(project_dir, 45)
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    walkthrough_path = os.path.join(target_dir, "walkthrough.md")
    
    assert os.path.exists(walkthrough_path)
    
    with open(walkthrough_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    sess3 = os.path.join(mock_brain_dir, "2466c0f9-3333")
    
    # Original absolute paths should be gone
    assert sess3 not in content
    assert f"file://{sess3}" not in content
    
    # Replaced with relative file names since they are in the same folder
    assert "![img1](./screenshot_1234.png)" in content
    assert '<img src="./walkthrough_img.jpg" />' in content
    assert "[link to task](./task.md)" in content

def test_sync_to_repo_uses_existing_feature_dir(mock_brain_dir, tmp_path):
    """When a feature dir already exists, sync into it."""
    project_dir = str(tmp_path / "repo2")
    os.makedirs(project_dir)
    
    existing_dir = os.path.join(project_dir, "docs", "features", "5_issue-45_cool-feature")
    os.makedirs(existing_dir)
    
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 45)
    
    assert len(synced_files) == 4  # md + images
    
    target_dir = os.path.join(existing_dir, "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "screenshot_1234.png"))

def test_sync_to_repo_with_explicit_session(mock_brain_dir, tmp_path):
    """Should use the explicit session_path instead of auto-detecting latest."""
    project_dir = str(tmp_path / "repo_explicit")
    os.makedirs(project_dir)
    
    old_session = os.path.join(mock_brain_dir, "2466c0f9-1111")
    synced_files = AntigravityBrain.sync_to_repo(project_dir, 99, session_path=old_session)
    
    assert len(synced_files) == 1  # Only task.md in old session
    
    target_dir = os.path.join(project_dir, "docs", "features", "99_issue-99", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    
    with open(os.path.join(target_dir, "task.md")) as f:
        assert "Old Issue" in f.read()

# --- Versioning ---

def test_sync_versioning_same_content_skips(mock_brain_dir, tmp_path):
    """If file content is identical, don't create a new version."""
    project_dir = str(tmp_path / "repo_ver1")
    os.makedirs(project_dir)
    
    synced1 = AntigravityBrain.sync_to_repo(project_dir, 45)
    assert len(synced1) == 4
    
    synced2 = AntigravityBrain.sync_to_repo(project_dir, 45)
    assert len(synced2) == 0

def test_sync_versioning_different_content_creates_v2(mock_brain_dir, tmp_path):
    """If file content changed, save as _v2."""
    project_dir = str(tmp_path / "repo_ver2")
    os.makedirs(project_dir)
    
    synced1 = AntigravityBrain.sync_to_repo(project_dir, 45)
    assert len(synced1) == 4
    
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
    monkeypatch.setattr("builtins.input", lambda _: "y")
    
    state = LumaState(project_key="1")
    state.active_issues = [IssueData(
        number=45, title="Test", html_url="", body="", project_item_id="", project_id="", repository=""
    )]
    
    project = {
        "name": "Test Project",
        "path": project_dir,
        "repo": "test/test"
    }
    
    result = action_sync_ai_brain(state, project)
    assert result is True
    
    target_dir = os.path.join(project_dir, "docs", "features", "45_issue-45", "ai_brain")
    assert os.path.exists(os.path.join(target_dir, "task.md"))
    assert os.path.exists(os.path.join(target_dir, "screenshot_1234.png"))
