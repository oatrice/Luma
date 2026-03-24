import pytest
from unittest.mock import MagicMock, patch
from luma_core.state_manager import LumaState, WorkflowPhase

@patch("luma_core.actions.transition_to", return_value=(True, ""))
@patch("luma_core.actions.action_generate_plan")
@patch("luma_core.actions.action_generate_spec")
@patch("luma_core.actions.action_refine_issue")
@patch("luma_core.actions.action_run_multi_agent_coding")
@patch("luma_core.actions.check_planning_artifacts", return_value={"analysis": False, "spec": False, "plan": False})
@patch("luma_core.actions.get_feature_dir", return_value="/mock/feature/dir")
@patch("luma_core.actions.auto_fill_issue_metrics")
@patch("luma_core.issue_metrics.get_issue_metrics")
@patch("builtins.input")
def test_guided_workflow_planning_multi_repo_picker(
    mock_input, mock_get_metrics, mock_auto_fill, mock_get_feature_dir, mock_check_artifacts,
    mock_multi_agent, mock_refine, mock_spec, mock_plan, mock_transition, capsys
):
    from luma_core.actions import action_guided_workflow
    import luma_core.actions as actions_module

    # 1. Repo picker input ("1,2") - which means RootRepo and WebRepo
    # 2. y (Run planning for RootRepo)
    # 3. n (Done coding?)
    inputs = iter(["1,2", "y", "n"])
    mock_input.side_effect = lambda _: next(inputs)

    # Setup State
    state = LumaState()
    state.phase = WorkflowPhase.IDLE
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    state.active_issues = [mock_issue]

    # Setup Projects
    root_project = {
        "name": "RootRepo",
        "path": "/mock/root",
        "repo": "org/root",
        "type": "monorepo_root",
        "sibling_repos": ["web_id", "backend_id"]
    }
    web_project = {
        "name": "WebRepo",
        "path": "/mock/web",
        "repo": "org/web",
    }
    backend_project = {
        "name": "BackendRepo",
        "path": "/mock/backend",
        "repo": "org/backend",
    }
    patched_projects = {
        "root_id": root_project,
        "web_id": web_project,
        "backend_id": backend_project
    }

    with patch.dict(actions_module.PROJECTS, patched_projects):
        try:
            action_guided_workflow(state, root_project)
        except StopIteration:
            pass  # Expected when inputs run out if not quitting properly

    captured = capsys.readouterr()
    
    # Assert Checkbox UI is printed
    assert "📂 Select repos for Planning:" in captured.out
    assert "[1] ✅ RootRepo" in captured.out
    assert "[2] ☐  WebRepo" in captured.out
    assert "[3] ☐  BackendRepo" in captured.out
    
    # Assert Planner agents were called exactly ONCE (for the root repo)
    assert mock_refine.call_count == 1
    assert mock_spec.call_count == 1
    assert mock_plan.call_count == 1
    
    # Assert the context contains target_planning_repos
    assert "target_planning_repos" in state.context
    assert len(state.context["target_planning_repos"]) == 2
    assert state.context["target_planning_repos"][0]["name"] == "RootRepo"
    assert state.context["target_planning_repos"][1]["name"] == "WebRepo"


@patch("luma_core.actions.transition_to", return_value=(True, ""))
@patch("luma_core.actions.action_generate_plan")
@patch("luma_core.actions.action_generate_spec")
@patch("luma_core.actions.action_refine_issue")
@patch("luma_core.actions.action_run_multi_agent_coding")
@patch("luma_core.actions.check_planning_artifacts", return_value={"analysis": False, "spec": False, "plan": False})
@patch("luma_core.actions.get_feature_dir", return_value="/mock/feature/dir")
@patch("luma_core.actions.auto_fill_issue_metrics")
@patch("luma_core.issue_metrics.get_issue_metrics")
@patch("builtins.input")
def test_guided_workflow_planning_single_repo(
    mock_input, mock_get_metrics, mock_auto_fill, mock_get_feature_dir, mock_check_artifacts,
    mock_multi_agent, mock_refine, mock_spec, mock_plan, mock_transition, capsys
):
    from luma_core.actions import action_guided_workflow

    # 1. y (Run planning for SingleRepo)
    # 2. n (Done coding?)
    inputs = iter(["y", "n"])
    mock_input.side_effect = lambda _: next(inputs)

    # Setup State
    state = LumaState()
    state.phase = WorkflowPhase.IDLE
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    state.active_issues = [mock_issue]

    # Setup Projects (Single Repo)
    single_project = {
        "name": "SingleRepo",
        "path": "/mock/single",
        "repo": "org/single",
    }

    try:
        action_guided_workflow(state, single_project)
    except StopIteration:
        pass

    captured = capsys.readouterr()
    
    # Assert Checkbox UI is NOT printed
    assert "📂 Select repos for Planning:" not in captured.out
    
    # Assert Planner agents were called once
    assert mock_refine.call_count == 1
