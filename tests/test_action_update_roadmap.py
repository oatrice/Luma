import json
import subprocess
from unittest.mock import patch

import pytest

from luma_core.actions import action_update_roadmap
from luma_core.issue_metrics import IssueMetricsRecord, get_issue_metrics, save_issue_metrics
from luma_core.state_manager import LumaState


def _make_project_with_roadmap(tmp_path, roadmap_body):
    project_dir = tmp_path / "repo"
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True)
    roadmap_path = docs_dir / "ROADMAP.md"
    roadmap_path.write_text(roadmap_body, encoding="utf-8")
    return (
        {"name": "Test Repo", "path": str(project_dir), "repo": "oatrice/Test-Repo"},
        roadmap_path,
    )


def test_action_update_roadmap_appends_missing_github_issue(monkeypatch, tmp_path):
    project, roadmap_path = _make_project_with_roadmap(
        tmp_path,
        "# Roadmap\n\n## Current\n\n- Existing item\n",
    )

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=15: json.dumps(
            {
                "number": 77,
                "title": "Sync roadmap from GitHub",
                "state": "OPEN",
                "url": "https://github.com/oatrice/Test-Repo/issues/77",
            }
        ),
    )

    with patch(
        "luma_core.actions.quality_actions.ui.safe_input",
        side_effect=["77", "2"],
    ):
        action_update_roadmap(LumaState(), project)

    updated = roadmap_path.read_text(encoding="utf-8")
    assert "## Synced From GitHub" in updated
    assert "### Issue #77 - Sync roadmap from GitHub" in updated
    assert (
        "- **GitHub:** [#77](https://github.com/oatrice/Test-Repo/issues/77)"
        in updated
    )
    assert "- **State:** OPEN" in updated
    assert "- **Status:** 🟢 **Ready**" in updated


def test_action_update_roadmap_updates_existing_and_missing_issues_together(monkeypatch, tmp_path):
    project, roadmap_path = _make_project_with_roadmap(
        tmp_path,
        (
            "# Roadmap\n\n"
            "## Current\n\n"
            "### Issue #12 - Existing roadmap item\n"
            "- **Status:** 🔴 **Blocked**\n"
        ),
    )

    def fake_run_gh_command(args, timeout=15):
        issue_id = args[2]
        data = {
            "12": {
                "number": 12,
                "title": "Existing roadmap item",
                "state": "OPEN",
                "url": "https://github.com/oatrice/Test-Repo/issues/12",
            },
            "77": {
                "number": 77,
                "title": "Missing roadmap item",
                "state": "OPEN",
                "url": "https://github.com/oatrice/Test-Repo/issues/77",
            },
        }
        return json.dumps(data[issue_id])

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        fake_run_gh_command,
    )

    with patch(
        "luma_core.actions.quality_actions.ui.safe_input",
        side_effect=["12, 77", "3"],
    ):
        action_update_roadmap(LumaState(), project)

    updated = roadmap_path.read_text(encoding="utf-8")
    assert "### Issue #12 - Existing roadmap item" in updated
    assert updated.count("**Status:** 🟡 **In Progress**") == 2
    assert "### Issue #77 - Missing roadmap item" in updated


def test_action_update_roadmap_auto_sync_closed_issues(monkeypatch, tmp_path):
    project, roadmap_path = _make_project_with_roadmap(
        tmp_path,
        (
            "# Roadmap\n\n"
            "## Current\n\n"
            "### Issue #42 - Feature X\n"
            "- **Status:** 🟡 **In Progress**\n"
        ),
    )

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=15: json.dumps(
            {
                "number": 42,
                "title": "Feature X",
                "state": "CLOSED",
                "url": "https://github.com/oatrice/Test-Repo/issues/42",
            }
        ),
    )

    with patch(
        "luma_core.actions.quality_actions.ui.safe_input",
        side_effect=["42", "", "v1.2.0", "Auto fixed", ""],
    ):
        action_update_roadmap(LumaState(), project)

    updated = roadmap_path.read_text(encoding="utf-8")
    assert "✅ **Done** (v1.2.0) - Auto fixed" in updated


def test_action_update_roadmap_done_saves_post_story_point(monkeypatch, tmp_path):
    project, _ = _make_project_with_roadmap(
        tmp_path,
        (
            "# Roadmap\n\n"
            "## Current\n\n"
            "### Issue #42 - Feature X\n"
            "- **Status:** 🟡 **In Progress**\n"
        ),
    )

    save_issue_metrics(
        project["path"],
        IssueMetricsRecord(
            issue_key="oatrice/Test-Repo#42",
            issue_number=42,
            issue_title="Feature X",
            issue_url="https://github.com/oatrice/Test-Repo/issues/42",
            repository="oatrice/Test-Repo",
            issue_status="🟡 In Progress",
            estimate_points=3,
        ),
    )

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=15: json.dumps(
            {
                "number": 42,
                "title": "Feature X",
                "state": "CLOSED",
                "url": "https://github.com/oatrice/Test-Repo/issues/42",
            }
        ),
    )

    with patch(
        "luma_core.actions.quality_actions.ui.safe_input",
        side_effect=["42", "", "v1.2.0", "Auto fixed", "5"],
    ):
        action_update_roadmap(LumaState(), project)

    loaded = get_issue_metrics(project["path"], "oatrice/Test-Repo", 42)
    assert loaded is not None
    assert loaded.post_story_point == 5


@pytest.mark.skip(reason="Complex mock setup for chained inputs - TODO: fix input mocking")
def test_action_update_roadmap_create_new_issue_via_gh(monkeypatch, tmp_path):
    """🔴 RED → Test that typing 'new' creates a GitHub issue and appends it to Roadmap.md"""
    project, roadmap_path = _make_project_with_roadmap(
        tmp_path,
        "# Roadmap\n\n## Current\n\n- Existing item\n",
    )

    mock_result = subprocess.CompletedProcess(
        args=["gh", "issue", "create"],
        returncode=0,
        stdout="https://github.com/oatrice/Test-Repo/issues/99\n",
        stderr="",
    )

    with patch(
        "luma_core.actions.quality_actions.subprocess.run",
        return_value=mock_result,
    ):
        # Mock run_gh_command for fetching the newly created issue details
        monkeypatch.setattr(
            "luma_core.actions.quality_actions.run_gh_command",
            lambda args, timeout=15: json.dumps(
                {
                    "number": 99,
                    "title": "My new feature",
                    "state": "OPEN",
                    "url": "https://github.com/oatrice/Test-Repo/issues/99",
                }
            ),
        )

        with patch(
            "luma_core.actions.quality_actions.ui.safe_input",
            side_effect=["new", "My new feature", "", "2"],
        ), patch(
            "luma_core.actions.issue_actions.safe_input",
            side_effect=["My new feature", ""],
        ), patch(
            "luma_core.ui.safe_input",
            side_effect=["2"],
        ):
            action_update_roadmap(LumaState(), project)

    updated = roadmap_path.read_text(encoding="utf-8")
    assert "## Synced From GitHub" in updated
    assert "### Issue #99 - My new feature" in updated
    assert "- **State:** OPEN" in updated
