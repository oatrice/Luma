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

