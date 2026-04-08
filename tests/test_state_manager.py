"""
Unit Tests for Luma V2 State Manager
"""

import pytest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luma_core.state_manager import (
    LumaState, IssueData, WorkflowPhase,
    save_state, load_state, clear_state,
    transition_to, can_transition,
    format_state_header, get_next_step_recommendation
)


class TestLumaState:
    """Test LumaState dataclass"""
    
    def test_default_state(self):
        state = LumaState()
        assert state.phase == WorkflowPhase.IDLE
        assert state.active_issue is None
        assert state.project_key == ""
    
    def test_state_with_issue(self):
        issue = IssueData(number=1, title="Test", html_url="http://test")
        state = LumaState(active_issues=[issue], phase=WorkflowPhase.CODING)
        assert state.active_issue.number == 1
        assert state.phase == WorkflowPhase.CODING


class TestSaveLoad:
    """Test save/load state functions"""
    
    def test_save_creates_file(self, tmp_path):
        state = LumaState(project_key="test")
        result = save_state(state, str(tmp_path))
        assert result
        assert (tmp_path / ".luma_state.json").exists()
    
    def test_load_nonexistent_returns_default(self, tmp_path):
        state = load_state(str(tmp_path))
        assert state.phase == WorkflowPhase.IDLE
    
    def test_load_corrupted_returns_default(self, tmp_path):
        state_file = tmp_path / ".luma_state.json"
        state_file.write_text("not valid json {{{")
        state = load_state(str(tmp_path))
        assert state.phase == WorkflowPhase.IDLE
    
    def test_save_load_roundtrip(self, tmp_path):
        issue = IssueData(number=42, title="Test Issue", html_url="http://test")
        original = LumaState(
            project_key="jarwise",
            phase=WorkflowPhase.CODING,
            active_issues=[issue],
            active_branch="feat/42"
        )
        
        save_state(original, str(tmp_path))
        loaded = load_state(str(tmp_path))
        
        assert loaded.project_key == "jarwise"
        assert loaded.phase == WorkflowPhase.CODING
        assert loaded.active_issue.number == 42
        assert loaded.active_branch == "feat/42"
    
    def test_clear_state(self, tmp_path):
        state = LumaState(project_key="test")
        save_state(state, str(tmp_path))
        
        assert (tmp_path / ".luma_state.json").exists()
        
        clear_state(str(tmp_path))
        assert not (tmp_path / ".luma_state.json").exists()


class TestTransitions:
    """Test state transition logic"""
    
    def test_valid_idle_to_selecting(self):
        state = LumaState()
        ok, msg = transition_to(state, WorkflowPhase.SELECTING)
        assert ok
        assert state.phase == WorkflowPhase.SELECTING
    
    def test_idle_to_coding_requires_data(self):
        """IDLE -> CODING is valid but requires active_issues and branch"""
        state = LumaState()
        ok, msg = transition_to(state, WorkflowPhase.CODING)
        assert not ok
        assert "Missing required" in msg
    
    def test_idle_to_coding_with_data(self):
        """IDLE -> CODING works with bootstrap data (headless mode)"""
        state = LumaState()
        issue = IssueData(number=1, title="Test", html_url="http://test")
        
        ok, msg = transition_to(
            state,
            WorkflowPhase.CODING,
            active_issues=[issue],
            active_branch="feat/1"
        )
        
        assert ok
        assert state.phase == WorkflowPhase.CODING
    
    def test_selecting_to_coding_requires_data(self):
        state = LumaState(phase=WorkflowPhase.SELECTING)
        ok, msg = transition_to(state, WorkflowPhase.CODING)
        assert not ok
        assert "Missing required" in msg
    
    def test_selecting_to_coding_with_data(self):
        state = LumaState(phase=WorkflowPhase.SELECTING)
        issue = IssueData(number=1, title="Test", html_url="http://test")
        
        ok, msg = transition_to(
            state, 
            WorkflowPhase.CODING,
            active_issues=[issue],
            active_branch="feat/1"
        )
        
        assert ok
        assert state.phase == WorkflowPhase.CODING
        assert state.active_issue.number == 1
        assert state.started_at is not None
    
    def test_idle_clears_data(self):
        issue = IssueData(number=1, title="Test", html_url="http://test")
        state = LumaState(
            phase=WorkflowPhase.PR_PENDING,
            active_issues=[issue],
            active_branch="feat/1",
            pr_url="http://pr"
        )
        
        ok, msg = transition_to(state, WorkflowPhase.IDLE)
        
        assert ok
        assert state.active_issue is None
        assert state.active_branch is None
        assert state.pr_url is None
    
    def test_can_transition_helper(self):
        assert can_transition(WorkflowPhase.IDLE, WorkflowPhase.SELECTING)
        assert can_transition(WorkflowPhase.IDLE, WorkflowPhase.CODING)  # Now valid for headless bootstrap
        assert can_transition(WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT)
        # REVIEWING phase transitions
        assert can_transition(WorkflowPhase.CODING, WorkflowPhase.REVIEWING)
        assert can_transition(WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT)
        assert can_transition(WorkflowPhase.REVIEWING, WorkflowPhase.CODING)

    def test_coding_to_reviewing(self):
        state = LumaState(phase=WorkflowPhase.CODING)
        ok, msg = transition_to(state, WorkflowPhase.REVIEWING)
        assert ok
        assert state.phase == WorkflowPhase.REVIEWING

    def test_reviewing_to_preflight(self):
        state = LumaState(phase=WorkflowPhase.REVIEWING)
        ok, msg = transition_to(state, WorkflowPhase.PREFLIGHT)
        assert ok
        assert state.phase == WorkflowPhase.PREFLIGHT


class TestDisplayFunctions:
    """Test display utility functions"""
    
    def test_format_state_header_idle(self):
        state = LumaState()
        header = format_state_header(state)
        assert "Idle" in header
    
    def test_format_state_header_with_issue(self):
        issue = IssueData(number=42, title="Test Issue Title", html_url="http://test")
        state = LumaState(
            phase=WorkflowPhase.CODING,
            active_issues=[issue],
            active_branch="feat/42"
        )
        header = format_state_header(state)
        assert "#42" in header
        assert "feat/42" in header
    
    def test_next_step_recommendations(self):
        for phase in WorkflowPhase:
            state = LumaState(phase=phase)
            rec = get_next_step_recommendation(state)
            assert len(rec) > 0


class TestMultiIssueMode:
    """Test Multi-Issue Mode (active_issues as list)"""

    def test_default_state_has_empty_issues_list(self):
        """active_issues should be empty list by default"""
        state = LumaState()
        assert state.active_issues == []
        assert state.active_issue is None  # property backward compat

    def test_state_with_multiple_issues(self):
        """Can create state with multiple issues"""
        issue1 = IssueData(number=68, title="Admin CRUD", html_url="http://test/68")
        issue2 = IssueData(number=69, title="Staff Mgmt", html_url="http://test/69")
        state = LumaState(
            active_issues=[issue1, issue2],
            phase=WorkflowPhase.CODING
        )
        assert len(state.active_issues) == 2
        assert state.active_issue.number == 68  # primary = first
        assert state.active_issues[1].number == 69

    def test_active_issue_property_returns_first(self):
        """active_issue property returns first issue in list"""
        issue1 = IssueData(number=10, title="First", html_url="http://1")
        issue2 = IssueData(number=20, title="Second", html_url="http://2")
        state = LumaState(active_issues=[issue1, issue2])
        assert state.active_issue == issue1

    def test_active_issue_property_returns_none_when_empty(self):
        """active_issue property returns None when list empty"""
        state = LumaState()
        assert state.active_issue is None

    def test_has_issues_property(self):
        """has_issues property returns True/False"""
        state = LumaState()
        assert state.has_issues is False

        issue = IssueData(number=1, title="Test", html_url="http://1")
        state.active_issues.append(issue)
        assert state.has_issues is True

    def test_save_load_roundtrip_multi_issue(self, tmp_path):
        """Save/load with multiple issues preserves all data"""
        issue1 = IssueData(number=68, title="Admin CRUD", html_url="http://68")
        issue2 = IssueData(number=69, title="Staff Mgmt", html_url="http://69")
        original = LumaState(
            project_key="jarwise",
            phase=WorkflowPhase.CODING,
            active_issues=[issue1, issue2],
            active_branch="feat/68-69-admin-content"
        )

        save_state(original, str(tmp_path))
        loaded = load_state(str(tmp_path))

        assert len(loaded.active_issues) == 2
        assert loaded.active_issues[0].number == 68
        assert loaded.active_issues[1].number == 69
        assert loaded.active_branch == "feat/68-69-admin-content"

    def test_backward_compat_load_single_issue_format(self, tmp_path):
        """Load old state format (active_issue dict) into active_issues list"""
        old_state = {
            "version": "1.0",
            "project_key": "jarwise",
            "phase": "coding",
            "active_issue": {
                "number": 42,
                "title": "Old Issue",
                "html_url": "http://test/42"
            },
            "active_branch": "feat/42",
            "checklist": {},
            "context": {},
            "last_updated": "2026-01-01T00:00:00"
        }
        state_file = tmp_path / ".luma_state.json"
        state_file.write_text(json.dumps(old_state))

        loaded = load_state(str(tmp_path))
        assert len(loaded.active_issues) == 1
        assert loaded.active_issues[0].number == 42
        assert loaded.active_issue.number == 42  # property compat

    def test_transition_to_coding_with_multi_issues(self):
        """Transition to CODING with multiple issues"""
        state = LumaState(phase=WorkflowPhase.SELECTING)
        issue1 = IssueData(number=68, title="Issue A", html_url="http://68")
        issue2 = IssueData(number=69, title="Issue B", html_url="http://69")

        ok, msg = transition_to(
            state,
            WorkflowPhase.CODING,
            active_issues=[issue1, issue2],
            active_branch="feat/68-69-issues"
        )

        assert ok is True
        assert len(state.active_issues) == 2

    def test_transition_to_idle_clears_issues_list(self):
        """Transition to IDLE clears active_issues"""
        issue = IssueData(number=1, title="Test", html_url="http://1")
        state = LumaState(
            phase=WorkflowPhase.PR_PENDING,
            active_issues=[issue],
            active_branch="feat/1",
            pr_url="http://pr"
        )

        ok, msg = transition_to(state, WorkflowPhase.IDLE)
        assert ok is True
        assert state.active_issues == []
        assert state.active_issue is None

    def test_format_header_multi_issue(self):
        """Header shows multiple issue numbers"""
        issue1 = IssueData(number=68, title="Admin CRUD", html_url="http://68")
        issue2 = IssueData(number=69, title="Staff Mgmt", html_url="http://69")
        state = LumaState(
            phase=WorkflowPhase.CODING,
            active_issues=[issue1, issue2],
            active_branch="feat/68-69"
        )
        header = format_state_header(state)
        assert "#68" in header
        assert "#69" in header


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
