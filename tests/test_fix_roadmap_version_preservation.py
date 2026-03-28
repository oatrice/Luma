import json
import pytest
from luma_core.actions.quality_actions import sync_roadmap_for_closed_issues, action_update_roadmap
from luma_core.state_manager import LumaState

def _make_project(tmp_path, roadmap_body, repo="oatrice/Test-Repo"):
    project_dir = tmp_path / "repo"
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True)
    roadmap_path = docs_dir / "ROADMAP.md"
    roadmap_path.write_text(roadmap_body, encoding="utf-8")
    return (
        {"name": "Test Repo", "path": str(project_dir), "repo": repo},
        roadmap_path,
    )

def test_sync_roadmap_preserves_version_in_table_row(monkeypatch, tmp_path):
    """
    Test that sync_roadmap_for_closed_issues preserves existing version (v0.1.0) 
    in a table row when updating to CLOSED status.
    """
    project, roadmap_path = _make_project(
        tmp_path,
        (
            "# Roadmap\n\n"
            "| Issue | Title | Status |\n"
            "|-------|-------|--------|\n"
            "| #42 | Feature X | ✅ Complete (v0.1.0) |\n"
        ),
    )

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=10: json.dumps(
            {"number": 42, "title": "Feature X", "state": "CLOSED",
             "url": "https://github.com/oatrice/Test-Repo/issues/42"}
        ),
    )

    sync_roadmap_for_closed_issues(project, [42])

    updated = roadmap_path.read_text(encoding="utf-8")
    # CURRENT BEHAVIOR: Overwrites with " ✅ Complete "
    # EXPECTED BEHAVIOR: Keeps " (v0.1.0) "
    assert "✅ Complete (v0.1.0)" in updated

def test_sync_roadmap_preserves_version_in_list_item(monkeypatch, tmp_path):
    """
    Test that sync_roadmap_for_closed_issues preserves existing version (v0.1.0)
    in a list item when updating to CLOSED status.
    """
    project, roadmap_path = _make_project(
        tmp_path,
        (
            "# Roadmap\n\n"
            "### Issue #42 - Feature X\n"
            "- **Status:** ✅ **Done** (v0.1.0)\n"
        ),
    )

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=10: json.dumps(
            {"number": 42, "title": "Feature X", "state": "CLOSED",
             "url": "https://github.com/oatrice/Test-Repo/issues/42"}
        ),
    )

    sync_roadmap_for_closed_issues(project, [42])

    updated = roadmap_path.read_text(encoding="utf-8")
    # CURRENT BEHAVIOR: Overwrites with "- ✅ **Done**\n"
    # EXPECTED BEHAVIOR: Keeps " (v0.1.0)"
    assert "✅ **Done** (v0.1.0)" in updated

def test_action_update_roadmap_preserves_existing_version_when_skipping_input(monkeypatch, tmp_path):
    """
    Test that action_update_roadmap preserves existing version (v0.1.0)
    when the user selects 'Done' but leaves version/note fields empty.
    """
    project, roadmap_path = _make_project(
        tmp_path,
        (
            "# Roadmap\n\n"
            "### Issue #42 - Feature X\n"
            "- **Status:** ✅ **Done** (v0.1.0)\n"
        ),
    )

    # Inputs: "42" (issue), "1" (Done), "" (version skip), "" (note skip)
    inputs = iter(["42", "1", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=15: json.dumps(
            {"number": 42, "title": "Feature X", "state": "CLOSED",
             "url": "https://github.com/oatrice/Test-Repo/issues/42"}
        ),
    )

    action_update_roadmap(LumaState(), project)

    updated = roadmap_path.read_text(encoding="utf-8")
    assert "✅ **Done** (v0.1.0)" in updated
