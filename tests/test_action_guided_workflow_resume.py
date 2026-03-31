import pytest
import os
from unittest.mock import patch, MagicMock

from luma_core.state_manager import LumaState, WorkflowPhase, IssueData

@pytest.fixture
def project_mock(tmp_path):
    return {
        "name": "TestProj",
        "path": str(tmp_path),
        "repo": "owner/repo"
    }

@patch("luma_core.actions.workflow_actions.action_select_issue")
@patch("luma_core.actions.workflow_actions.get_feature_dir")
@patch("luma_core.actions.workflow_actions.check_planning_artifacts")
@patch("luma_core.actions.workflow_actions.action_generate_plan")
@patch("luma_core.actions.workflow_actions.action_run_multi_agent_coding")
@patch("luma_core.actions.workflow_actions.action_code_review")
@patch("luma_core.actions.workflow_actions.action_update_docs")
@patch("luma_core.actions.workflow_actions.action_update_roadmap")
@patch("luma_core.actions.workflow_actions.action_archive_artifacts")
@patch("luma_core.actions.workflow_actions.action_create_pr")
@patch("luma_core.github_project.check_pr_merged")
@patch("luma_core.issue_metrics.sync_github_metrics_for_project")
@patch("luma_core.issue_metrics.prefill_metrics_from_roadmap")
@patch("luma_core.notifier.notify_task_complete")
@patch("luma_core.metrics_summarizer.summarize_usage_stats")
@patch("luma_core.metrics_summarizer.summarize_issue_metrics")
@patch("luma_core.metrics_summarizer.format_summary_message")
# @patch("builtins.print")
@patch("builtins.input")
def test_guided_workflow_resume_from_review(
    mock_input, mock_format, mock_sum_metrics, mock_sum_usage, mock_notify,
    mock_prefill, mock_sync_gh, mock_check_merged, mock_pr, mock_archive, mock_roadmap,
    mock_docs, mock_review, mock_swarm, mock_plan, mock_check_plan, mock_get_feature_dir, mock_select,
    project_mock
):
    from luma_core.actions import action_guided_workflow

    # State is already past coding (e.g. step_coding is done, or phase is REVIEWING)
    state = LumaState(
        project_key="1",
        phase=WorkflowPhase.REVIEWING,
        active_issues=[IssueData(number=1, title="Test", html_url="url")],
    )
    # The checklist indicates planning and coding are done
    state.checklist["step_planning"] = True
    state.checklist["step_coding"] = True

    # User answers "y" to all remaining prompts
    # 1. Check AI estimation? -> n
    # 2. Run Code Review? -> y
    # 3. Update Docs? -> y
    # 4. Sync AI Brain? -> y
    # 5. Update Roadmap? -> y
    # 6. Archive? -> y
    # 7. Create PRs? -> y
    # 8. Check CI? -> n
    # 9. Press enter after merged -> ""
    mock_input.side_effect = ["n", "y", "y", "y", "y", "y", "y", "n", ""]

    mock_check_plan.return_value = {"analysis": True, "spec": True, "plan": True}
    mock_get_feature_dir.return_value = "/mock/feature/dir"
    mock_check_merged.return_value = {"merged": True}
    mock_prefill.return_value = {"created": 0, "updated": 0}
    mock_sync_gh.return_value = {"updated": 0}

    action_guided_workflow(state, project_mock)

    # It should NOT call planning or multi-agent coding
    mock_plan.assert_not_called()
    mock_swarm.assert_not_called()

    # It SHOULD call review, docs, roadmap, archive, pr
    mock_review.assert_called_once()
    mock_docs.assert_called_once()
    mock_roadmap.assert_called_once()
    mock_archive.assert_called_once()
    mock_notify.assert_called_once()
