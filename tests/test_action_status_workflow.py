from unittest.mock import patch

from luma_core.actions import action_list_active_issues, action_select_issue
from luma_core.github_project import KanbanCard
from luma_core.state_manager import LumaState


def _luma_project():
    return {
        "name": "Luma",
        "path": "/Users/oatrice/Software-projects/Luma",
        "repo": "oatrice/Luma",
        "kanban_number": 5,
        "kanban_id": "PVT_kwHOATfKEM4BKOOI",
    }


@patch("builtins.input", return_value="1")
@patch("luma_core.actions._start_issues", return_value=True)
@patch("luma_core.actions.fetch_kanban_cards")
def test_action_select_issue_respects_luma_workflow(
    mock_fetch,
    mock_start_issues,
    _mock_input,
):
    mock_fetch.return_value = [
        KanbanCard(item_id="1", issue_number=1, title="Backlog Task", status="Backlog", repository="r", url="u"),
        KanbanCard(item_id="2", issue_number=2, title="Review Task", status="In Review", repository="r", url="u"),
        KanbanCard(item_id="3", issue_number=3, title="Ready Task", status="Ready", repository="r", url="u"),
        KanbanCard(item_id="4", issue_number=4, title="Progress Task", status="In Progress", repository="r", url="u"),
        KanbanCard(item_id="5", issue_number=5, title="Done Task", status="Done", repository="r", url="u"),
    ]

    result = action_select_issue(LumaState(), _luma_project())

    assert result is True
    selected_cards = mock_start_issues.call_args.args[1]
    assert [card.issue_number for card in selected_cards] == [4]


@patch("luma_core.actions.fetch_kanban_cards")
def test_action_list_active_issues_includes_in_review_for_luma(mock_fetch, capsys):
    mock_fetch.return_value = [
        KanbanCard(item_id="1", issue_number=1, title="Done Task", status="Done", repository="repo", url="url"),
        KanbanCard(item_id="2", issue_number=2, title="Backlog Task", status="Backlog", repository="repo", url="url"),
        KanbanCard(item_id="3", issue_number=3, title="Review Task", status="In Review", repository="repo", url="url"),
        KanbanCard(item_id="4", issue_number=4, title="Ready Task", status="Ready", repository="repo", url="url"),
        KanbanCard(item_id="5", issue_number=5, title="Progress Task", status="In Progress", repository="repo", url="url"),
    ]

    action_list_active_issues(_luma_project())
    output = capsys.readouterr().out

    assert "In Review" in output
    assert "Done Task" not in output
    assert output.index("Progress Task") < output.index("Ready Task")
    assert output.index("Ready Task") < output.index("Review Task")
