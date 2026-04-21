import os
import subprocess
import tempfile
from typing import Optional
from unittest.mock import MagicMock, patch

from luma_core.actions import _build_code_review_followup_prompt


def test_build_code_review_followup_prompt_single_repo():
    prompt = _build_code_review_followup_prompt()

    assert (
        prompt
        == "นำ code review จาก code_review.md "
        "(อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) มาอธิบาย "
        "และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย "
        "ถ้า code_review.md ไม่ make sense ให้ใช้ draft_code_review.md แทน"
    )
    assert "terminal" not in prompt


def test_build_code_review_followup_prompt_multi_repo():
    prompt = _build_code_review_followup_prompt(multi_repo=True)

    assert (
        prompt
        == "นำ code review จาก code_review.md "
        "(อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) ในทุก repo มาอธิบาย "
        "และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย "
        "ถ้า code_review.md ไม่ make sense ให้ใช้ draft_code_review.md แทน"
    )
    assert "terminal" not in prompt


# ── Tests for repo selection in action_code_review ────────────────────────────


def _make_state(context: Optional[dict] = None):
    """Helper: build a minimal LumaState-like mock."""
    state = MagicMock()
    state.context = context or {}
    state.active_issues = []
    return state


def _make_project(name: str = "MonoRoot", project_type: str = "monorepo_root") -> dict:
    return {"name": name, "path": "/tmp/fake_repo", "type": project_type}


@patch("luma_core.actions.quality_actions.get_git_changed_files", return_value=[])
def test_action_code_review_uses_preselected_repos_without_prompt(
    mock_changed_files,
):
    """
    🟢 GREEN: When state.context["target_planning_repos"] is set,
    action_code_review must NOT call input() and must review exactly
    those repos.
    """
    from luma_core.actions import action_code_review

    project_a = {"name": "RepoA", "path": "/tmp/repo_a", "type": "unknown"}
    project_b = {"name": "RepoB", "path": "/tmp/repo_b", "type": "unknown"}

    state = _make_state(context={"target_planning_repos": [project_a, project_b]})

    with patch("builtins.input") as mock_input:
        action_code_review(state, project_a)

    # Should NOT ask for repo selection
    for call_args in mock_input.call_args_list:
        prompt_text = call_args[0][0] if call_args[0] else ""
        assert "Select repositories to review" not in prompt_text, (
            "input() should not ask for repo selection when preselected_repos exists"
        )


@patch("luma_core.actions.quality_actions.get_git_changed_files", return_value=[])
def test_action_code_review_fallback_asks_when_no_preselected(
    mock_changed_files,
    monkeypatch,
):
    """
    🟢 GREEN: When state.context has no target_planning_repos AND project
    has sibling_repos, action_code_review MUST ask the user to select.
    """
    from luma_core.actions import action_code_review, PROJECTS

    sibling = {"name": "SiblingRepo", "path": "/tmp/sibling", "type": "unknown"}
    PROJECTS["sib1"] = sibling

    project = {
        "name": "MonoRoot",
        "path": "/tmp/monorepo",
        "type": "monorepo_root",
        "sibling_repos": ["sib1"],
    }

    state = _make_state(context={})  # no preselected

    with patch("builtins.input", return_value="") as mock_input:
        action_code_review(state, project)

    # Should have asked for repo selection at some point
    asked_for_selection = any(
        "Select" in (call_args[0][0] if call_args[0] else "")
        for call_args in mock_input.call_args_list
    )
    assert asked_for_selection, "Should prompt for repo selection when no preselected_repos"


@patch("luma_core.actions.quality_actions.get_git_changed_files", return_value=[".luma_metrics.json"])
@patch("luma_core.agents.reviewer.reviewer_agent")
def test_action_code_review_headless_skips_generated_metrics_file(
    mock_reviewer_agent,
    mock_changed_files,
):
    """
    🟥 RED: Headless code review should ignore generated Luma metrics files so
    machine callers can get a clean success path without invoking the reviewer.
    """
    from luma_core.actions import action_code_review

    project = _make_project(name="RepoA", project_type="unknown")
    state = _make_state()

    result = action_code_review(state, project, headless=True)

    assert result["summary"]["clean_count"] == 1
    assert result["projects"][0]["status"] == "clean"
    assert result["projects"][0]["changed_files"] == []
    mock_reviewer_agent.assert_not_called()


def test_action_code_review_headless_preserves_external_repo_paths_from_worktree_context():
    """
    🟥 RED: Headless multi-repo code review must only remap paths for the same
    git repository family as the active worktree. External repos must keep
    their own configured paths in the result payload.
    """
    from luma_core.actions import action_code_review

    def init_git_repo(path: str, filename: str = "README.md"):
        subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
        with open(os.path.join(path, filename), "w", encoding="utf-8") as handle:
            handle.write("# test\n")
        subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        luma_main = os.path.join(tmpdir, "Luma")
        luma_worktree = os.path.join(tmpdir, "Luma-worktrees", "luma1")
        jarwise_root = os.path.join(tmpdir, "JarWise")
        jarwise_web = os.path.join(tmpdir, "JarWise-Web")

        os.makedirs(luma_main)
        os.makedirs(os.path.dirname(luma_worktree), exist_ok=True)
        os.makedirs(jarwise_root)
        os.makedirs(jarwise_web)

        init_git_repo(luma_main)
        init_git_repo(jarwise_root)
        init_git_repo(jarwise_web)

        subprocess.run(
            ["git", "worktree", "add", "-b", "feat/headless-review", luma_worktree],
            cwd=luma_main,
            capture_output=True,
            check=True,
        )

        try:
            state = _make_state(
                context={
                    "target_planning_repos": [
                        {"name": "Luma", "path": luma_main, "type": "unknown"},
                        {"name": "JarWise-Root", "path": jarwise_root, "type": "unknown"},
                        {"name": "JarWise-Web", "path": jarwise_web, "type": "unknown"},
                    ]
                }
            )
            project = {"name": "Luma", "path": luma_main, "type": "unknown"}

            with patch("os.getcwd", return_value=luma_worktree):
                with patch(
                    "luma_core.actions.quality_actions.get_git_changed_files",
                    return_value=[],
                ):
                    result = action_code_review(state, project, headless=True)

            projects = {item["name"]: item for item in result["projects"]}

            assert os.path.realpath(projects["Luma"]["path"]) == os.path.realpath(luma_worktree)
            assert os.path.realpath(projects["JarWise-Root"]["path"]) == os.path.realpath(jarwise_root)
            assert os.path.realpath(projects["JarWise-Web"]["path"]) == os.path.realpath(jarwise_web)
            assert {item["status"] for item in result["projects"]} == {"clean"}
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "-f", luma_worktree],
                cwd=luma_main,
                capture_output=True,
            )
