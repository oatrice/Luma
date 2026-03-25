from luma_core.actions import action_manage_issue_metrics
from luma_core.github_project import KanbanCard
from luma_core.issue_metrics import get_issue_metrics, save_issue_metrics, IssueMetricsRecord
from luma_core.state_manager import LumaState


def test_action_manage_issue_metrics_lists_tracked_issues(monkeypatch, tmp_path, capsys):
    project = {
        "name": "Metrics Repo",
        "path": str(tmp_path),
        "repo": "oatrice/Metrics",
        "kanban_number": 99,
    }

    save_issue_metrics(
        str(tmp_path),
        IssueMetricsRecord(
            issue_key="oatrice/Metrics#21",
            issue_number=21,
            issue_title="Track me",
            issue_url="https://github.com/oatrice/Metrics/issues/21",
            repository="oatrice/Metrics",
            project_name="Metrics Repo",
            estimate_points=5,
            effort_level="High",
        ),
    )

    monkeypatch.setattr(
        "luma_core.actions.metrics_actions.prefill_metrics_from_roadmap",
        lambda path, name, repo: {"created": 0, "updated": 0},
    )
    inputs = iter(["1", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    action_manage_issue_metrics(LumaState(), project)
    output = capsys.readouterr().out

    assert "Tracked Issues for Metrics Repo" in output
    assert "#21" in output
    assert "Track me" in output


def test_action_manage_issue_metrics_saves_selected_issue(monkeypatch, tmp_path):
    project = {
        "name": "Metrics Repo",
        "path": str(tmp_path),
        "repo": "oatrice/Metrics",
        "kanban_number": 99,
        "status_workflow": {},
    }

    monkeypatch.setattr(
        "luma_core.actions.metrics_actions.prefill_metrics_from_roadmap",
        lambda path, name, repo: {"created": 0, "updated": 0},
    )
    monkeypatch.setattr(
        "luma_core.actions.utils.fetch_kanban_cards",
        lambda _kanban_number: [
            KanbanCard(
                item_id="1",
                issue_number=50,
                title="Keep this repo only",
                status="Ready",
                repository="oatrice/Metrics",
                url="https://github.com/oatrice/Metrics/issues/50",
            ),
            KanbanCard(
                item_id="2",
                issue_number=51,
                title="Other repo issue",
                status="Ready",
                repository="oatrice/Other",
                url="https://github.com/oatrice/Other/issues/51",
            ),
        ],
    )

    inputs = iter(
        [
            "2",
            "1",
            "8",
            "3.5",
            "1.25",
            "2026-03-20 14:30",
            "2026-03-21 18:00",
            "High",
            "Ready to ship",
            "0",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    action_manage_issue_metrics(LumaState(), project)

    saved = get_issue_metrics(str(tmp_path), "oatrice/Metrics", 50)
    assert saved is not None
    assert saved.issue_title == "Keep this repo only"
    assert saved.estimate_points == 8
    assert saved.estimated_mandays == 3.5
    assert saved.actual_mandays == 1.25
    assert saved.due_date == "2026-03-20T14:30:00"
    assert saved.actual_completion_date == "2026-03-21T18:00:00"
    assert saved.effort_level == "High"
    assert saved.notes == "Ready to ship"


def test_action_manage_issue_metrics_prefills_from_roadmap(monkeypatch, tmp_path, capsys):
    project = {
        "name": "Metrics Repo",
        "path": str(tmp_path),
        "repo": "oatrice/Metrics",
        "kanban_number": 99,
        "status_workflow": {},
    }

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "| ID | Title | Status |\n"
        "|---|---|---|\n"
        "| [#77](#77) | Prefilled from roadmap | 🔲 Todo |\n",
        encoding="utf-8",
    )

    inputs = iter(["1", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    action_manage_issue_metrics(LumaState(), project)
    output = capsys.readouterr().out
    saved = get_issue_metrics(str(tmp_path), "oatrice/Metrics", 77)

    assert "Prefilled issue metrics from ROADMAP.md" in output
    assert saved is not None
    assert saved.issue_title == "Prefilled from roadmap"
    assert saved.issue_status == "🔲 Todo"
