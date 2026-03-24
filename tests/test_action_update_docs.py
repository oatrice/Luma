from luma_core.actions import action_update_docs
from luma_core.state_manager import LumaState

def test_action_update_docs_uses_planning_repos_from_context(monkeypatch):
    called_repos = []

    def mock_update_multi_repo_docs(target_repos, docs_agent_func):
        called_repos.extend(target_repos)
        return []

    monkeypatch.setattr(
        "luma_core.actions.update_multi_repo_docs", mock_update_multi_repo_docs
    )
    monkeypatch.setattr(
        "luma_core.actions.refresh_pending_doc_updates", lambda s, p: None
    )

    root_project = {
        "name": "Root Project",
        "type": "monorepo_root",
        "sibling_repos": ["sib1", "sib2"],
    }
    sibling_project = {"name": "Sibling 1"}

    state = LumaState()
    # Mock that planning phase selected only root and sib1
    state.context["target_planning_repos"] = [root_project, sibling_project]

    monkeypatch.setattr(
        "luma_core.actions.PROJECTS",
        {"str_sib1": sibling_project, "str_sib2": {"name": "Sibling 2"}},
    )

    action_update_docs(state, root_project, skip_confirm=True)

    assert len(called_repos) == 2
    assert called_repos[0]["name"] == "Root Project"
    assert called_repos[1]["name"] == "Sibling 1"

def test_action_update_docs_fallback_when_no_context(monkeypatch):
    called_repos = []

    def mock_update_multi_repo_docs(target_repos, docs_agent_func):
        called_repos.extend(target_repos)
        return []

    monkeypatch.setattr(
        "luma_core.actions.update_multi_repo_docs", mock_update_multi_repo_docs
    )
    monkeypatch.setattr(
        "luma_core.actions.refresh_pending_doc_updates", lambda s, p: None
    )

    root_project = {
        "name": "Root",
        "type": "monorepo_root",
        "sibling_repos": ["sib1", "sib2"],
    }
    sibling1 = {"name": "Sib1"}
    sibling2 = {"name": "Sib2"}

    state = LumaState()
    # No target_planning_repos in context

    monkeypatch.setattr(
        "luma_core.actions.PROJECTS",
        {"sib1": sibling1, "sib2": sibling2},
    )

    action_update_docs(state, root_project, skip_confirm=True)

    # By default, skip_confirm=True means it should use all_candidates
    assert len(called_repos) == 3
    assert called_repos[0]["name"] == "Root"
    assert called_repos[1]["name"] == "Sib1"
    assert called_repos[2]["name"] == "Sib2"
