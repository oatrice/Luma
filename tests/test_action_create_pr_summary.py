from unittest.mock import MagicMock, patch
from luma_core.state_manager import LumaState, WorkflowPhase

# Try to import PreflightCheckResult for mocking
try:
    from luma_core.actions import PreflightCheckResult
except ImportError:
    class PreflightCheckResult:
        def __init__(self, name, passed, message):
            self.name = name
            self.passed = passed
            self.message = message


@patch("luma_core.actions.workflow_actions.transition_to", return_value=(True, ""))
@patch("luma_core.actions.workflow_actions.PreflightChecker")
@patch("luma_core.actions.workflow_actions._confirm_pending_doc_updates_before_pr", return_value=True)
@patch("subprocess.run")
@patch("luma_core.github_client.get_open_pr", return_value=None)
@patch("luma_core.actions.workflow_actions.publisher_agent")
def test_action_create_pr_summary_printed(
    mock_publisher, mock_get_open_pr, mock_subprocess, mock_confirm_docs,
    mock_preflight, mock_transition, capsys
):
    from luma_core.actions import action_create_pr
    import luma_core.actions as actions_module

    # Mock PreflightChecker
    mock_checker_inst = MagicMock()
    mock_checker_inst.run_checks.return_value = [PreflightCheckResult("Test Check", True, "OK")]
    mock_preflight.return_value = mock_checker_inst

    # Mock subprocess.run for git commands
    def fake_subprocess_run(args, **kwargs):
        mock_res = MagicMock()
        mock_res.returncode = 0
        if "branch" in args:
            mock_res.stdout = "feat/test-branch\n"
        elif "rev-list" in args:
            mock_res.stdout = "1\n"
        return mock_res
    mock_subprocess.side_effect = fake_subprocess_run

    # Mock publisher agent
    def fake_publisher(state_dict):
        repo = state_dict.get("repo", "unknown")
        return {"pr_url": f"https://github.com/mock/{repo}/pull/1"}
    mock_publisher.side_effect = fake_publisher

    # Setup State
    state = LumaState()
    state.phase = WorkflowPhase.CODING
    state.active_branch = "feat/test-branch"
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = "Body"
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

    # Patch PROJECTS dictionary
    patched_projects = {
        "root_id": root_project,
        "web_id": web_project,
        "backend_id": backend_project
    }

    with patch.dict(actions_module.PROJECTS, patched_projects):
        action_create_pr(state, root_project, auto_approve=True)

    captured = capsys.readouterr()
    
    # Assert PR Summary is printed
    assert "📋 PR Summary:" in captured.out
    assert "✅ RootRepo" in captured.out
    assert "https://github.com/mock/org/root/pull/1" in captured.out
    assert "✅ WebRepo" in captured.out
    assert "https://github.com/mock/org/web/pull/1" in captured.out
    assert "✅ BackendRepo" in captured.out
    assert "https://github.com/mock/org/backend/pull/1" in captured.out
