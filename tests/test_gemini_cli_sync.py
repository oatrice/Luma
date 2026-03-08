import os
import json
import pytest
from luma_core.ai_brain_sync import GeminiCLIBrain

@pytest.fixture
def mock_gemini_session(tmp_path, monkeypatch):
    """Setup mock Gemini CLI session JSON."""
    gemini_root = tmp_path / "gemini_tmp"
    luma_chats = gemini_root / "luma" / "chats"
    luma_chats.mkdir(parents=True)
    
    session_data = {
        "sessionId": "test-session-123",
        "startTime": "2026-03-08T03:11:46.675Z",
        "messages": [
            {
                "type": "user",
                "content": [{"text": "Hello, plan something."}]
            },
            {
                "type": "gemini",
                "content": "Here is the plan:\n1. Step one\n2. Step two",
                "thoughts": [
                    {
                        "subject": "Planning",
                        "description": "I am planning the steps.",
                        "timestamp": "2026-03-08T03:11:50.156Z"
                    }
                ]
            }
        ]
    }
    
    sess_file = luma_chats / "session-2026-03-08T03-09-test.json"
    sess_file.write_text(json.dumps(session_data))
    
    monkeypatch.setattr(GeminiCLIBrain, "DEFAULT_SESSION_PATH", str(luma_chats))
    return str(luma_chats)

def test_gemini_get_latest_session(mock_gemini_session):
    latest = GeminiCLIBrain.get_latest_session()
    assert latest is not None
    assert "session-2026-03-08T03-09-test.json" in latest

def test_gemini_sync_creates_markdown(mock_gemini_session, tmp_path):
    project_dir = str(tmp_path / "project")
    os.makedirs(project_dir)
    
    # We'll use issue number 8 for testing
    synced_files = GeminiCLIBrain.sync_to_repo(project_dir, 8)
    
    assert len(synced_files) > 0
    
    target_dir = os.path.join(project_dir, "docs", "features", "8_issue-8", "ai_brain")
    chat_log = os.path.join(target_dir, "gemini_chat_log.md")
    
    assert os.path.exists(chat_log)
    content = open(chat_log).read()
    assert "Hello, plan something." in content
    assert "Here is the plan:" in content
    assert "I am planning the steps." in content
