import pytest
from unittest.mock import MagicMock, patch
from luma_core.state_manager import LumaState, WorkflowPhase
from luma_core.issue_metrics import IssueMetricsRecord

@patch("luma_core.actions.transition_to", return_value=(True, ""))
@patch("luma_core.actions.action_generate_plan")
@patch("luma_core.actions.action_generate_spec")
@patch("luma_core.actions.action_refine_issue")
@patch("luma_core.actions.action_run_multi_agent_coding")
@patch("luma_core.actions.check_planning_artifacts", return_value={"analysis": False, "spec": False, "plan": False})
@patch("luma_core.actions.get_feature_dir", return_value="/mock/feature/dir")
@patch("luma_core.issue_metrics.get_issue_metrics")
@patch("luma_core.actions.auto_fill_issue_metrics")
@patch("builtins.input")
def test_guided_workflow_asks_for_metrics_auto_fill(
    mock_input, mock_auto_fill, mock_get_metrics, mock_get_feature_dir, mock_check_artifacts,
    mock_multi_agent, mock_refine, mock_spec, mock_plan, mock_transition, capsys
):
    from luma_core.actions import action_guided_workflow

    # 1. 'y' to run planning phase
    # 2. 'y' to auto-fill missing metrics
    inputs = iter(["y", "y", "0"]) # 0 to skip coding
    
    def mock_input_func(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return ""
            
    mock_input.side_effect = mock_input_func

    # Mock metrics so estimate_points is None
    mock_get_metrics.return_value = IssueMetricsRecord(
        issue_key="org/single#1",
        issue_number=1,
        repository="org/single",
        project_name="SingleRepo",
        issue_title="Test Issue",
        issue_url="https://github.com/org/single/issues/1"
    )

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

    action_guided_workflow(state, single_project)

    captured = capsys.readouterr()
    
    # Assert Checkbox UI is printed for metrics
    assert "การประเมินชั่วโมงการทำงาน" in captured.out
    
    # Assert auto_fill function is called
    mock_auto_fill.assert_called_once()
