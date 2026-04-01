import json
from types import SimpleNamespace
from unittest.mock import patch

from luma_core.actions import action_list_active_issues, action_select_issue
from luma_core.github_project import KanbanCard
from luma_core.state_manager import LumaState
import luma_core.usage_tracker as usage_tracker


def _luma_project():
    return {
        "name": "Luma",
        "path": "/Users/oatrice/Software-projects/Luma",
        "repo": "oatrice/Luma",
        "kanban_number": 5,
        "kanban_id": "PVT_kwHOATfKEM4BKOOI",
    }


@patch("builtins.input", return_value="1")
@patch("luma_core.actions.issue_actions._start_issues", return_value=True)
@patch("luma_core.actions.issue_actions.fetch_kanban_cards")
def test_action_select_issue_respects_luma_workflow(
    mock_fetch,
    mock_start_issues,
    _mock_input,
    capsys,
):
    mock_fetch.return_value = [
        KanbanCard(item_id="1", issue_number=1, title="Backlog Task", status="Backlog", repository="r", url="u"),
        KanbanCard(item_id="2", issue_number=2, title="Review Task", status="In Review", repository="r", url="u"),
        KanbanCard(item_id="3", issue_number=3, title="Ready Task", status="Ready", repository="r", url="u"),
        KanbanCard(item_id="4", issue_number=4, title="Progress Task", status="In Progress", repository="r", url="u"),
        KanbanCard(item_id="5", issue_number=5, title="Done Task", status="Done", repository="r", url="u"),
    ]

    result = action_select_issue(LumaState(), _luma_project())
    output = capsys.readouterr().out

    assert result is True
    assert "เช็ค gh cli, Roadmap.md ว่าต้องทำ issue ไหนต่อ" in output
    selected_cards = mock_start_issues.call_args.args[1]
    assert [card.issue_number for card in selected_cards] == [4]


@patch("luma_core.actions.issue_actions.fetch_kanban_cards")
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


@patch("luma_core.actions.issue_actions.fetch_kanban_cards")
def test_action_select_issue_shows_blocking_status_summary(mock_fetch, capsys):
    mock_fetch.return_value = [
        KanbanCard(item_id="1", issue_number=7, title="Upgrade Luma v2 from cli to Web UI", status="Backlog", repository="r", url="u"),
        KanbanCard(item_id="2", issue_number=8, title="Add Support for OpenRouter LLM Provider", status="Backlog", repository="r", url="u"),
        KanbanCard(item_id="3", issue_number=9, title="Tracking Estimate Points", status="Backlog", repository="r", url="u"),
    ]

    result = action_select_issue(LumaState(), _luma_project())
    output = capsys.readouterr().out

    assert result is False
    assert "เช็ค gh cli, Roadmap.md ว่าต้องทำ issue ไหนต่อ" in output
    assert "No 'Ready', 'In Progress' issues found on Kanban." in output
    assert "Available elsewhere on the board:" in output
    assert "- Backlog: 3" in output
    assert "#7: Upgrade Luma v2 from cli to Web UI" in output
    assert "Move a card to Ready or In Progress" in output


def test_action_select_issue_logs_branch_generation_with_action_context(
    monkeypatch,
    tmp_path,
):
    log_path = tmp_path / ".luma_ai_usage.jsonl"
    project = _luma_project()
    project["path"] = str(tmp_path)

    workflow = {
        "selectable_statuses": ["Ready", "In Progress"],
        "selection_order": ["In Progress", "Ready"],
        "board_order": ["Backlog", "Ready", "In Progress", "Done"],
        "done_statuses": ["Done", "Closed"],
        "status_icons": {},
        "action_status_map": {},
    }

    class DummySummarizer:
        def __init__(self, _path):
            pass

        def summarize_rules(self):
            return []

    def fake_generate_branch_names(title, body, issue_number):
        usage_tracker.record_llm_event(
            provider="test-provider",
            model="test-model",
            status="success",
            purpose="code",
        )
        return [f"feat/{issue_number}-smart-branch"]

    monkeypatch.setattr(
        usage_tracker,
        "get_log_path",
        lambda: str(log_path),
    )
    monkeypatch.setattr(
        "luma_core.actions.issue_actions.fetch_kanban_cards",
        lambda _kanban_number: [
            KanbanCard(
                item_id="2",
                issue_number=42,
                title="Improve usage logging",
                body="Ensure select issue branch suggestion logs action context.",
                status="In Progress",
                repository="oatrice/Luma",
                url="https://github.com/oatrice/Luma/issues/42",
            )
        ],
    )
    monkeypatch.setattr(
        "luma_core.actions.issue_actions.get_status_workflow",
        lambda _project: workflow,
    )
    monkeypatch.setattr(
        "luma_core.actions.utils.get_status_workflow",
        lambda _project: workflow,
    )
    monkeypatch.setattr(
        "luma_core.actions.issue_actions.sync_roadmap_for_closed_issues",
        lambda _project, _issue_numbers: 0,
    )
    monkeypatch.setattr(
        "luma_core.actions.issue_actions.sync_roadmap_for_new_issues",
        lambda _project, _cards: 0,
    )
    monkeypatch.setattr(
        "luma_core.actions.issue_actions.safe_input",
        lambda _prompt="": "1",
    )
    monkeypatch.setattr(
        "luma_core.actions.utils.ui.safe_input",
        lambda _prompt="": "1",
    )
    monkeypatch.setattr(
        "luma_core.actions.utils.ContextSummarizer",
        DummySummarizer,
    )
    monkeypatch.setattr(
        "luma_core.agents.analyst.generate_branch_names",
        fake_generate_branch_names,
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    usage_tracker.clear_action()
    usage_tracker.clear_sub_action()
    usage_tracker.clear_context()

    result = action_select_issue(LumaState(), project)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert result is True
    assert len(lines) == 1

    event = json.loads(lines[0])
    assert event["action"] == "Select Issue"
    assert event["sub_action"] == "SelectIssue/BranchSuggestion"
    assert event["purpose"] == "code"
