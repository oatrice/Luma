import os
import json
import pytest
from luma_core.context_summarizer import ContextSummarizer

@pytest.fixture
def mock_project(tmp_path):
    # Setup .luma_rules.json
    rules = {
        "context_rules": ["Remember to drink water"],
        "preflight_checks": [
            {"name": "Check Version", "required": True, "message": "Version must pass"}
        ]
    }
    with open(tmp_path / ".luma_rules.json", "w") as f:
        json.dump(rules, f)
        
    # Setup agent dir
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    (agent_dir / "rules").mkdir()
    
    # Setup markdown rule
    md_content = """
    # Rules
    - Developers MUST wash hands
    - You SHOULD sleep early
    > [!IMPORTANT]
    > Backup database
    """
    with open(agent_dir / "rules" / "test_rule.md", "w") as f:
        f.write(md_content)
        
    return str(tmp_path)

def test_context_summarizer(mock_project):
    summarizer = ContextSummarizer(mock_project)
    
    reminders = summarizer.summarize_rules(limit=10)
    
    # Check JSON rules
    assert any("Remember to drink water" in r for r in reminders)
    assert any("Version must pass" in r for r in reminders)
    
    # Check Markdown rules
    assert any("MUST: Developers MUST wash hands" in r for r in reminders)
    assert any("SHOULD: You SHOULD sleep early" in r for r in reminders)
    assert any("IMPORTANT: Backup database" in r for r in reminders)

def test_no_rules_file(tmp_path):
    summarizer = ContextSummarizer(str(tmp_path))
    reminders = summarizer.summarize_rules()
    assert reminders == []
