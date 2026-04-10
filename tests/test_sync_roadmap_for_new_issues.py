"""
TDD Tests for sync_roadmap_for_new_issues

🟥 RED: Written before implementing the helper.
🟢 GREEN: Passes after sync_roadmap_for_new_issues is added to quality_actions.py.
"""
import math
from luma_core.actions.quality_actions import sync_roadmap_for_new_issues


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


def _card(number, title, status="Ready", url=None):
    """Simple dict to simulate a KanbanCard-like object."""
    from types import SimpleNamespace
    return SimpleNamespace(
        issue_number=number,
        title=title,
        status=status,
        url=url or f"https://github.com/oatrice/Test-Repo/issues/{number}",
        body="",
        repository="oatrice/Test-Repo",
    )


def test_new_issue_not_in_roadmap_is_appended(tmp_path, monkeypatch):
    """🟥 RED → OPEN issue not in Roadmap.md should be appended"""
    project, roadmap_path = _make_project(
        tmp_path,
        "# Roadmap\n\n## Current\n\n- Existing item\n",
    )
    # Mock resolve_project_target_dir to return project path directly (avoid CI worktree redirect)
    monkeypatch.setattr(
        "luma_core.actions.quality_actions.resolve_project_target_dir",
        lambda path: path,
    )

    cards = [_card(55, "Brand New Feature", status="Ready")]
    synced = sync_roadmap_for_new_issues(project, cards)

    assert synced == 1
    updated = roadmap_path.read_text(encoding="utf-8")
    assert "### Issue #55 - Brand New Feature" in updated
    assert "🟢 **Ready**" in updated or "Ready" in updated


def test_existing_issue_in_roadmap_is_skipped(tmp_path):
    """🟥 RED → Issue already in Roadmap.md must NOT be duplicated"""
    project, roadmap_path = _make_project(
        tmp_path,
        (
            "# Roadmap\n\n"
            "### Issue #10 - Already here\n"
            "- **Status:** 🟡 **In Progress**\n"
        ),
    )
    original = roadmap_path.read_text(encoding="utf-8")

    cards = [_card(10, "Already here", status="In Progress")]
    synced = sync_roadmap_for_new_issues(project, cards)

    assert synced == 0
    assert roadmap_path.read_text(encoding="utf-8") == original


def test_multiple_new_issues_all_appended(tmp_path, monkeypatch):
    """🟥 RED → Multiple new issues should all be appended"""
    project, roadmap_path = _make_project(
        tmp_path,
        "# Roadmap\n\n## Current\n",
    )
    # Mock resolve_project_target_dir to return project path directly (avoid CI worktree redirect)
    monkeypatch.setattr(
        "luma_core.actions.quality_actions.resolve_project_target_dir",
        lambda path: path,
    )

    cards = [
        _card(100, "Feature Alpha", status="Ready"),
        _card(101, "Feature Beta", status="In Progress"),
    ]
    synced = sync_roadmap_for_new_issues(project, cards)

    assert synced == 2
    updated = roadmap_path.read_text(encoding="utf-8")
    assert "### Issue #100 - Feature Alpha" in updated
    assert "### Issue #101 - Feature Beta" in updated


def test_mixed_existing_and_new(tmp_path, monkeypatch):
    """🟥 RED → Only NEW issues are appended, existing ones skipped"""
    project, roadmap_path = _make_project(
        tmp_path,
        (
            "# Roadmap\n\n"
            "### Issue #20 - Old feature\n"
            "- **Status:** 🟡 **In Progress**\n"
        ),
    )
    # Mock resolve_project_target_dir to return project path directly (avoid CI worktree redirect)
    monkeypatch.setattr(
        "luma_core.actions.quality_actions.resolve_project_target_dir",
        lambda path: path,
    )

    cards = [
        _card(20, "Old feature", status="In Progress"),
        _card(21, "New feature", status="Ready"),
    ]
    synced = sync_roadmap_for_new_issues(project, cards)

    assert synced == 1
    updated = roadmap_path.read_text(encoding="utf-8")
    assert "### Issue #21 - New feature" in updated
    assert updated.count("### Issue #20") == 1  # ไม่ duplicate


def test_returns_zero_when_no_roadmap(tmp_path):
    """🟥 RED → Returns 0 gracefully when no Roadmap.md"""
    project = {"name": "Test", "path": str(tmp_path / "no-repo"), "repo": "oatrice/Test"}
    cards = [_card(1, "Test")]

    synced = sync_roadmap_for_new_issues(project, cards)
    assert synced == 0


def test_returns_zero_for_empty_cards(tmp_path):
    """🟥 RED → Empty cards list returns 0"""
    project, _ = _make_project(tmp_path, "# Roadmap\n")
    synced = sync_roadmap_for_new_issues(project, [])
    assert synced == 0
