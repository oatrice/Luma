from unittest.mock import MagicMock, patch
from luma_core.state_manager import LumaState, WorkflowPhase

@patch("luma_core.actions.workflow_actions.transition_to", return_value=(True, ""))
@patch("luma_core.actions.workflow_actions.action_generate_plan")
@patch("luma_core.actions.workflow_actions.action_generate_spec")
@patch("luma_core.actions.workflow_actions.action_refine_issue")
@patch("luma_core.actions.workflow_actions.action_run_multi_agent_coding")
@patch("luma_core.actions.workflow_actions.sync_planning_metrics_for_issues")
@patch("luma_core.actions.workflow_actions.check_planning_artifacts", return_value={"analysis": False, "spec": False, "plan": False})
@patch("luma_core.actions.workflow_actions.get_feature_dir", return_value="/mock/feature/dir")
@patch("builtins.input")
def test_guided_workflow_syncs_planning_metrics_after_planning(
    mock_input, mock_get_feature_dir, mock_check_artifacts, mock_sync_planning_metrics,
    mock_multi_agent, mock_refine, mock_spec, mock_plan, mock_transition, capsys, tmp_path
):
    from luma_core.actions import action_guided_workflow

    # 1. Run planning phase
    # 2. Pause at coding phase after planning is complete
    inputs = iter(["y", "n"])
    
    def mock_input_func(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return ""
            
    mock_input.side_effect = mock_input_func

    # Setup State
    state = LumaState()
    state.phase = WorkflowPhase.IDLE
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.html_url = "https://github.com/org/single/issues/1"
    state.active_issues = [mock_issue]

    # Setup Projects (Single Repo)
    single_project = {
        "name": "SingleRepo",
        "path": str(tmp_path),
        "repo": "org/single",
    }

    action_guided_workflow(state, single_project)

    capsys.readouterr()

    mock_sync_planning_metrics.assert_called_once_with(
        str(tmp_path),
        "SingleRepo",
        "org/single",
        state.active_issues,
    )

@patch("luma_core.actions.workflow_actions.transition_to", return_value=(True, ""))
@patch("luma_core.actions.workflow_actions.action_generate_plan")
@patch("luma_core.actions.workflow_actions.action_generate_spec")
@patch("luma_core.actions.workflow_actions.action_refine_issue")
@patch("luma_core.actions.workflow_actions.action_run_multi_agent_coding")
@patch("luma_core.actions.workflow_actions.check_planning_artifacts", return_value={"analysis": True, "spec": True, "plan": True})
@patch("luma_core.actions.workflow_actions.sync_planning_metrics_for_issues")
@patch("luma_core.actions.workflow_actions.get_feature_dir", return_value="/mock/feature/dir")
@patch("builtins.input")
def test_guided_workflow_existing_artifacts_os_error(
    mock_input, mock_get_feature_dir, mock_sync_planning_metrics, mock_check_artifacts,
    mock_multi_agent, mock_refine, mock_spec, mock_plan, mock_transition, capsys, tmp_path
):
    from luma_core.actions import action_guided_workflow

    # '0' to skip planning, '0' to skip coding
    # Note: the input sequence might need to match the prompts in 'workflow_branch'
    inputs = iter(["0", "0"]) 
    
    def mock_input_func(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return ""
            
    mock_input.side_effect = mock_input_func

    # Setup State
    state = LumaState()
    state.phase = WorkflowPhase.IDLE
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.html_url = "https://github.com/org/single/issues/1"
    state.active_issues = [mock_issue]

    # Setup Projects (Single Repo)
    single_project = {
        "name": "SingleRepo",
        "path": str(tmp_path),
        "repo": "org/single",
    }

    # This should raised UnboundLocalError previously
    action_guided_workflow(state, single_project)

    captured = capsys.readouterr()
    assert "Found existing Planning Docs" in captured.out
    mock_sync_planning_metrics.assert_called_once()
