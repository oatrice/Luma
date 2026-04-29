import unittest
from unittest.mock import MagicMock, patch
from luma_core.actions.issue_actions import action_add_issue
from luma_core.state_manager import LumaState
from luma_core.state_manager import WorkflowPhase, IssueData


class MockCard:
    def __init__(self, issue_number, title, url, body, item_id, repository, status):
        self.issue_number = issue_number
        self.title = title
        self.url = url
        self.body = body
        self.item_id = item_id
        self.repository = repository
        self.status = status


class TestActionAddIssue(unittest.TestCase):
    def test_add_multiple_issues_comma_separated_original(self):
        # Setup state
        state = LumaState()
        state.phase = WorkflowPhase.CODING
        state.active_issues = []  # empty

        project = {"kanban_number": 1, "kanban_id": "kanban_id"}

        # Mock selectable cards
        selectable = [
            MockCard(61, "Title1", "url1", "body1", "item1", "repo", "Ready"),
            MockCard(62, "Title2", "url2", "body2", "item2", "repo", "Ready"),
            MockCard(63, "Title3", "url3", "body3", "item3", "repo", "Ready"),
        ]

        # Mock inputs: "1,2,3"
        with patch(
            "luma_core.actions.issue_actions.fetch_kanban_cards", return_value=[]
        ) as mock_fetch:
            with patch(
                "luma_core.actions.issue_actions._get_selectable_cards",
                return_value=selectable,
            ) as mock_select:
                with patch(
                    "luma_core.actions.issue_actions.safe_input", return_value="1,2,3"
                ) as mock_input:
                    with patch(
                        "luma_core.actions.issue_actions.sync_kanban_on_action"
                    ) as mock_sync:
                        result = action_add_issue(state, project)

        # Assert
        self.assertTrue(result)
        self.assertEqual(len(state.active_issues), 3)
        self.assertEqual(state.active_issues[0].number, 61)
        self.assertEqual(state.active_issues[1].number, 62)
        self.assertEqual(state.active_issues[2].number, 63)

        # Verify sync called 3 times
        self.assertEqual(mock_sync.call_count, 3)

    def test_add_multiple_issues_comma_separated(self):
        # Setup state
        state = LumaState()
        state.phase = WorkflowPhase.CODING
        state.active_issues = []  # empty

        project = {"kanban_number": 1, "kanban_id": "kanban_id"}

        # Mock selectable cards
        selectable = [
            MockCard(61, "Title1", "url1", "body1", "item1", "repo", "Ready"),
            MockCard(62, "Title2", "url2", "body2", "item2", "repo", "Ready"),
            MockCard(63, "Title3", "url3", "body3", "item3", "repo", "Ready"),
        ]

        # Mock inputs: "1,2,3"
        with patch(
            "luma_core.actions.issue_actions.fetch_kanban_cards", return_value=[]
        ) as mock_fetch:
            with patch(
                "luma_core.actions.issue_actions._get_selectable_cards",
                return_value=selectable,
            ) as mock_select:
                with patch(
                    "luma_core.actions.issue_actions.safe_input", return_value="1,2,3"
                ) as mock_input:
                    with patch(
                        "luma_core.actions.issue_actions.sync_kanban_on_action"
                    ) as mock_sync:
                        result = action_add_issue(state, project)

        # Assert
        self.assertTrue(result)
        self.assertEqual(len(state.active_issues), 3)
        self.assertEqual(state.active_issues[0].number, 61)
        self.assertEqual(state.active_issues[1].number, 62)
        self.assertEqual(state.active_issues[2].number, 63)

        # Verify sync called 3 times
        self.assertEqual(mock_sync.call_count, 3)
