import json

from luma_core.actions import action_update_roadmap
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

    inputs = iter(["77", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(
        "luma_core.actions.run_gh_command",
        lambda args, timeout=15: json.dumps(
            {
                "number": 77,
                "title": "Sync roadmap from GitHub",
                "state": "OPEN",
                "url": "https://github.com/oatrice/Test-Repo/issues/77",
            }
        ),
    )

    action_update_roadmap(LumaState(), project)

    updated = roadmap_path.read_text(encoding="utf-8")
    assert "## Synced From GitHub" in updated
    assert "### Issue #77 - Sync roadmap from GitHub" in updated
    assert "- **GitHub:** [#77](https://github.com/oatrice/Test-Repo/issues/77)" in updated
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

    inputs = iter(["12, 77", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

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

    monkeypatch.setattr("luma_core.actions.run_gh_command", fake_run_gh_command)

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

    # Empty string at second input simulates user pressing Enter to accept default Option 1 Mode
    inputs = iter(["42", "", "v1.2.0", "Auto fixed"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    monkeypatch.setattr(
        "luma_core.actions.run_gh_command",
        lambda args, timeout=15: json.dumps(
            {
                "number": 42,
                "title": "Feature X",
                "state": "CLOSED",
                "url": "https://github.com/oatrice/Test-Repo/issues/42",
            }
        ),
    )

    action_update_roadmap(LumaState(), project)

    updated = roadmap_path.read_text(encoding="utf-8")
    assert "✅ **Done** (v1.2.0) - Auto fixed" in updated

