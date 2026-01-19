"""
Unit Tests for Luma V2 GitHub Project Integration
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from luma_core.github_project import (
    KanbanCard, KNOWN_PROJECTS,
    get_project_config, fetch_kanban_cards,
    get_current_in_progress, get_ready_issues,
    run_gh_command, display_kanban_cards
)


class TestKanbanCard:
    """Test KanbanCard dataclass"""
    
    def test_create_card(self):
        card = KanbanCard(
            item_id="PVTI_123",
            issue_number=42,
            title="Test Issue",
            status="Ready",
            repository="oatrice/test",
            url="http://test"
        )
        assert card.issue_number == 42
        assert card.status == "Ready"
    
    def test_card_optional_body(self):
        card = KanbanCard(
            item_id="1", issue_number=1, title="t",
            status="Ready", repository="r", url="u"
        )
        assert card.body is None


class TestProjectConfig:
    """Test project configuration"""
    
    def test_jarwise_config(self):
        config = get_project_config("jarwise")
        assert config is not None
        assert config["number"] == 7
        assert config["owner"] == "oatrice"
    
    def test_tetris_config(self):
        config = get_project_config("tetris")
        assert config is not None
        assert config["number"] == 6
    
    def test_unknown_project(self):
        config = get_project_config("unknown")
        assert config is None
    
    def test_case_insensitive(self):
        assert get_project_config("JarWise") is not None
        assert get_project_config("JARWISE") is not None


class TestFetchKanbanCards:
    """Test fetch_kanban_cards with mocked gh CLI"""
    
    @patch('luma_core.github_project.run_gh_command')
    def test_fetch_returns_cards(self, mock_run):
        mock_run.return_value = json.dumps({
            "items": [
                {
                    "id": "PVTI_1",
                    "title": "Test Issue",
                    "status": "Ready",
                    "content": {
                        "type": "Issue",
                        "number": 42,
                        "repository": "oatrice/test",
                        "url": "http://test",
                        "title": "Test Issue"
                    }
                }
            ]
        })
        
        cards = fetch_kanban_cards(7)
        assert len(cards) == 1
        assert cards[0].issue_number == 42
        assert cards[0].status == "Ready"
    
    @patch('luma_core.github_project.run_gh_command')
    def test_fetch_filters_by_status(self, mock_run):
        mock_run.return_value = json.dumps({
            "items": [
                {"id": "1", "status": "Ready", "content": {"type": "Issue", "number": 1, "repository": "r", "url": "u", "title": "t1"}},
                {"id": "2", "status": "Done", "content": {"type": "Issue", "number": 2, "repository": "r", "url": "u", "title": "t2"}},
            ]
        })
        
        cards = fetch_kanban_cards(7, status_filter="Ready")
        assert len(cards) == 1
        assert cards[0].issue_number == 1
    
    @patch('luma_core.github_project.run_gh_command')
    def test_fetch_skips_non_issues(self, mock_run):
        mock_run.return_value = json.dumps({
            "items": [
                {"id": "1", "status": "Ready", "content": {"type": "Issue", "number": 1, "repository": "r", "url": "u", "title": "t"}},
                {"id": "2", "status": "Ready", "content": {"type": "DraftIssue", "number": 2, "title": "Draft"}},
            ]
        })
        
        cards = fetch_kanban_cards(7)
        assert len(cards) == 1
    
    @patch('luma_core.github_project.run_gh_command')
    def test_fetch_handles_empty(self, mock_run):
        mock_run.return_value = json.dumps({"items": []})
        cards = fetch_kanban_cards(7)
        assert cards == []
    
    @patch('luma_core.github_project.run_gh_command')
    def test_fetch_handles_error(self, mock_run):
        mock_run.return_value = None
        cards = fetch_kanban_cards(7)
        assert cards == []


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @patch('luma_core.github_project.fetch_kanban_cards')
    def test_get_current_in_progress(self, mock_fetch):
        mock_fetch.return_value = [
            KanbanCard(
                item_id="1", issue_number=42, title="Active Task",
                status="In Progress", repository="r", url="u"
            )
        ]
        
        current = get_current_in_progress(7)
        assert current is not None
        assert current.issue_number == 42
        mock_fetch.assert_called_with(7, "oatrice", status_filter="In Progress")
    
    @patch('luma_core.github_project.fetch_kanban_cards')
    def test_get_current_in_progress_none(self, mock_fetch):
        mock_fetch.return_value = []
        assert get_current_in_progress(7) is None
    
    @patch('luma_core.github_project.fetch_kanban_cards')
    def test_get_ready_issues(self, mock_fetch):
        mock_fetch.return_value = [
            KanbanCard(item_id="1", issue_number=1, title="t", status="Ready", repository="r", url="u"),
            KanbanCard(item_id="2", issue_number=2, title="t", status="Ready", repository="r", url="u"),
        ]
        
        ready = get_ready_issues(7)
        assert len(ready) == 2
        mock_fetch.assert_called_with(7, "oatrice", status_filter="Ready")


class TestDisplayFunctions:
    """Test display functions"""
    
    def test_display_empty_cards(self, capsys):
        display_kanban_cards([])
        captured = capsys.readouterr()
        assert "No cards found" in captured.out
    
    def test_display_cards(self, capsys):
        cards = [
            KanbanCard(item_id="1", issue_number=42, title="Test Issue", status="Ready", repository="r", url="u"),
        ]
        display_kanban_cards(cards)
        captured = capsys.readouterr()
        assert "#42" in captured.out
        assert "Test Issue" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
