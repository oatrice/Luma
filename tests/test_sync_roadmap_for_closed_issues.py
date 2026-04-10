"""
TDD Tests for sync_roadmap_for_closed_issues

🟥 RED: Written before implementing the helper.
🟢 GREEN: Passes after sync_roadmap_for_closed_issues is added to quality_actions.py.
"""
import json

from luma_core.actions.quality_actions import sync_roadmap_for_closed_issues


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


def test_sync_roadmap_updates_existing_issue_to_done(monkeypatch, tmp_path):
    """🟥 RED → Closed issue already in Roadmap should have status updated to ✅ Done"""
    project, roadmap_path = _make_project(
        tmp_path,
        (
            "# Roadmap\n\n"
            "## Current\n\n"
            "### Issue #42 - Feature X\n"
            "- **Status:** 🟡 **In Progress**\n"
        ),
    )
    # Mock resolve_project_target_dir to return project path directly (avoid CI worktree redirect)
    monkeypatch.setattr(
        "luma_core.actions.quality_actions.resolve_project_target_dir",
        lambda path: path,
    )

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=10: json.dumps(
            {"number": 42, "title": "Feature X", "state": "CLOSED",
             "url": "https://github.com/oatrice/Test-Repo/issues/42"}
        ),
    )

    synced = sync_roadmap_for_closed_issues(project, [42])

    assert synced == 1
    updated = roadmap_path.read_text(encoding="utf-8")
    assert "✅ **Done**" in updated


def test_sync_roadmap_appends_missing_closed_issue(monkeypatch, tmp_path):
    """🟥 RED → Closed issue NOT in Roadmap should be appended as ✅ Done"""
    project, roadmap_path = _make_project(
        tmp_path,
        "# Roadmap\n\n## Current\n\n- Existing item\n",
    )
    # Mock resolve_project_target_dir to return project path directly (avoid CI worktree redirect)
    monkeypatch.setattr(
        "luma_core.actions.quality_actions.resolve_project_target_dir",
        lambda path: path,
    )

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=10: json.dumps(
            {"number": 99, "title": "New Closed Feature", "state": "CLOSED",
             "url": "https://github.com/oatrice/Test-Repo/issues/99"}
        ),
    )

    synced = sync_roadmap_for_closed_issues(project, [99])

    assert synced == 1
    updated = roadmap_path.read_text(encoding="utf-8")
    assert "### Issue #99 - New Closed Feature" in updated
    assert "✅ **Done**" in updated


def test_sync_roadmap_skips_open_issues(monkeypatch, tmp_path):
    """🟥 RED → OPEN issues must NOT be touched"""
    project, roadmap_path = _make_project(
        tmp_path,
        (
            "# Roadmap\n\n"
            "### Issue #7 - Open Work\n"
            "- **Status:** 🟡 **In Progress**\n"
        ),
    )
    original = roadmap_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda args, timeout=10: json.dumps(
            {"number": 7, "title": "Open Work", "state": "OPEN",
             "url": "https://github.com/oatrice/Test-Repo/issues/7"}
        ),
    )

    synced = sync_roadmap_for_closed_issues(project, [7])

    assert synced == 0
    assert roadmap_path.read_text(encoding="utf-8") == original


def test_sync_roadmap_returns_zero_when_no_roadmap(monkeypatch, tmp_path):
    """🟥 RED → Returns 0 gracefully when Roadmap.md does not exist"""
    project = {"name": "Test", "path": str(tmp_path / "no-repo"), "repo": "oatrice/Test-Repo"}

    synced = sync_roadmap_for_closed_issues(project, [42])

    assert synced == 0


def test_sync_roadmap_handles_empty_issue_list(monkeypatch, tmp_path):
    """🟥 RED → Empty list should return 0 without calling gh cli"""
    project, _ = _make_project(tmp_path, "# Roadmap\n")

    called = []
    monkeypatch.setattr(
        "luma_core.actions.quality_actions.run_gh_command",
        lambda *a, **kw: called.append(1) or "",
    )

    synced = sync_roadmap_for_closed_issues(project, [])

    assert synced == 0
    assert called == []
