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
        state = LumaState(active_issue=issue, phase=WorkflowPhase.CODING)
        assert state.active_issue.number == 1
        assert state.phase == WorkflowPhase.CODING


class TestSaveLoad:
    """Test save/load state functions"""
    
    def test_save_creates_file(self, tmp_path):
        state = LumaState(project_key="test")
        result = save_state(state, str(tmp_path))
        assert result == True
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
            active_issue=issue,
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
        assert ok == True
        assert state.phase == WorkflowPhase.SELECTING
    
    def test_invalid_idle_to_coding(self):
        state = LumaState()
        ok, msg = transition_to(state, WorkflowPhase.CODING)
        assert ok == False
        assert "Cannot transition" in msg
    
    def test_selecting_to_coding_requires_data(self):
        state = LumaState(phase=WorkflowPhase.SELECTING)
        ok, msg = transition_to(state, WorkflowPhase.CODING)
        assert ok == False
        assert "Missing required" in msg
    
    def test_selecting_to_coding_with_data(self):
        state = LumaState(phase=WorkflowPhase.SELECTING)
        issue = IssueData(number=1, title="Test", html_url="http://test")
        
        ok, msg = transition_to(
            state, 
            WorkflowPhase.CODING,
            active_issue=issue,
            active_branch="feat/1"
        )
        
        assert ok == True
        assert state.phase == WorkflowPhase.CODING
        assert state.active_issue.number == 1
        assert state.started_at is not None
    
    def test_idle_clears_data(self):
        issue = IssueData(number=1, title="Test", html_url="http://test")
        state = LumaState(
            phase=WorkflowPhase.PR_PENDING,
            active_issue=issue,
            active_branch="feat/1",
            pr_url="http://pr"
        )
        
        ok, msg = transition_to(state, WorkflowPhase.IDLE)
        
        assert ok == True
        assert state.active_issue is None
        assert state.active_branch is None
        assert state.pr_url is None
    
    def test_can_transition_helper(self):
        assert can_transition(WorkflowPhase.IDLE, WorkflowPhase.SELECTING) == True
        assert can_transition(WorkflowPhase.IDLE, WorkflowPhase.CODING) == False
        assert can_transition(WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT) == True


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
            active_issue=issue,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
