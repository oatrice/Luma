"""
Tests for Select Issue worktree path resolution.
Issue #64: Fix worktree support for Select Issue action

TDD Red Phase: These tests should FAIL initially until we implement the fix.
"""
import os
import subprocess
import tempfile
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestSelectIssueWorktreePath:
    """Test that _start_issues() respects worktree path for git operations."""

    def test_start_issues_uses_worktree_path_for_git_checkout(self):
        """
        When running from a worktree, _start_issues() should perform git checkout
        in the worktree directory, not the main repository.
        """
        from luma_core.actions.utils import _start_issues
        from luma_core.state_manager import LumaState, WorkflowPhase

        with tempfile.TemporaryDirectory() as main_repo:
            # Setup main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)
            
            # Create initial commit
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Main Repo")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            # Create worktree
            worktree_path = os.path.join(main_repo, "..", "worktree_test")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/test", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                # Mock state and card
                state = MagicMock(spec=LumaState)
                state.phase = WorkflowPhase.IDLE
                state.active_issues = []
                state.active_branch = None
                state.context = {}
                
                card = MagicMock()
                card.issue_number = 123
                card.title = "Test Issue"
                card.body = "Test body"
                card.url = "https://github.com/test/issues/123"
                card.item_id = None
                card.repository = "test/repo"

                # Project config pointing to main_repo (simulating PROJECTS config)
                project = {"name": "TestProject", "path": main_repo, "repo": "test/repo"}

                # Track which directory git commands are executed in
                executed_dirs = []
                original_run = subprocess.run
                
                def tracking_run(*args, **kwargs):
                    if args and args[0] and isinstance(args[0], list):
                        cmd = args[0]
                        if cmd[0] == "git" and kwargs.get("cwd"):
                            executed_dirs.append(kwargs["cwd"])
                    return original_run(*args, **kwargs)

                # Run from worktree context (simulating user running Luma from worktree)
                with patch("os.getcwd", return_value=worktree_path):
                    with patch("luma_core.actions.utils.transition_to") as mock_transition:
                        with patch("luma_core.actions.utils.ui.safe_input", return_value="1"):
                            with patch("subprocess.run", side_effect=tracking_run):
                                with patch("luma_core.agents.analyst.generate_branch_names", return_value=["feat/123-test-issue"]):
                                    mock_transition.return_value = (True, None)
                                    _start_issues(state, [card], project)

                # Verify git commands were executed in worktree, not main repo
                git_dirs = [d for d in executed_dirs if d]
                
                # At least one git command should be in worktree
                assert any(
                    os.path.realpath(d) == os.path.realpath(worktree_path) 
                    for d in git_dirs
                ), f"Expected git commands in worktree {worktree_path}, but got: {git_dirs}"
                
                # No git command should be in main repo (when we have worktree)
                # Note: This test might fail initially because current implementation 
                # uses project["path"] (main_repo) instead of resolved worktree path
                main_repo_real = os.path.realpath(main_repo)
                for d in git_dirs:
                    if os.path.realpath(d) == main_repo_real:
                        pytest.fail(f"Git command executed in main repo {d} instead of worktree. Current implementation doesn't respect worktree path.")

            finally:
                # Cleanup worktree
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)

    def test_start_issues_headless_uses_worktree_path(self):
        """
        When running from a worktree in headless mode, 
        _start_issues_headless() should perform git operations in worktree.
        """
        from luma_core.actions.utils import _start_issues_headless
        from luma_core.state_manager import LumaState, WorkflowPhase

        with tempfile.TemporaryDirectory() as main_repo:
            # Setup main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)
            
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Main Repo")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            # Create worktree
            worktree_path = os.path.join(main_repo, "..", "worktree_headless")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/headless", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                state = MagicMock(spec=LumaState)
                state.phase = WorkflowPhase.IDLE
                state.active_issues = []
                state.active_branch = None
                state.context = {}
                
                card = MagicMock()
                card.issue_number = 456
                card.title = "Headless Test Issue"
                card.body = "Test body"
                card.url = "https://github.com/test/issues/456"
                card.item_id = None
                card.repository = "test/repo"

                project = {"name": "TestProject", "path": main_repo, "repo": "test/repo"}

                executed_dirs = []
                original_run = subprocess.run
                
                def tracking_run(*args, **kwargs):
                    if args and args[0] and isinstance(args[0], list):
                        cmd = args[0]
                        if cmd[0] == "git" and kwargs.get("cwd"):
                            executed_dirs.append(kwargs["cwd"])
                    return original_run(*args, **kwargs)

                with patch("os.getcwd", return_value=worktree_path):
                    with patch("luma_core.actions.utils.transition_to") as mock_transition:
                        with patch("subprocess.run", side_effect=tracking_run):
                            with patch("luma_core.agents.analyst.generate_branch_names", return_value=["feat/456-headless-test"]):
                                mock_transition.return_value = (True, None)
                                _start_issues_headless(state, [card], project, branch_name="feat/456-headless-test")

                git_dirs = [d for d in executed_dirs if d]
                
                # Should use worktree path
                assert any(
                    os.path.realpath(d) == os.path.realpath(worktree_path) 
                    for d in git_dirs
                ), f"Expected git commands in worktree {worktree_path}, but got: {git_dirs}"

                main_repo_real = os.path.realpath(main_repo)
                for d in git_dirs:
                    if os.path.realpath(d) == main_repo_real:
                        pytest.fail(f"Git command executed in main repo {d} instead of worktree. Headless mode doesn't respect worktree path.")

            finally:
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)

    def test_start_issues_headless_saves_state_in_worktree_path(self):
        """
        When running from a worktree in headless mode,
        state should be saved into the worktree path, not the main repository.
        """
        from luma_core.actions.utils import _start_issues_headless
        from luma_core.state_manager import LumaState, WorkflowPhase

        with tempfile.TemporaryDirectory() as main_repo:
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)

            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Main Repo")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            worktree_path = os.path.join(main_repo, "..", "worktree_save_state")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/save-state", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                state = MagicMock(spec=LumaState)
                state.phase = WorkflowPhase.IDLE
                state.active_issues = []
                state.active_branch = None
                state.context = {}

                card = MagicMock()
                card.issue_number = 789
                card.title = "Save State Issue"
                card.body = "Test body"
                card.url = "https://github.com/test/issues/789"
                card.item_id = None
                card.repository = "test/repo"

                project = {"name": "TestProject", "path": main_repo, "repo": "test/repo"}

                with patch("os.getcwd", return_value=worktree_path):
                    with patch("luma_core.actions.utils.transition_to") as mock_transition:
                        with patch("luma_core.actions.utils.save_state", return_value=True) as mock_save_state:
                            mock_transition.return_value = (True, None)
                            _start_issues_headless(
                                state,
                                [card],
                                project,
                                branch_name="feat/789-save-state",
                            )

                mock_save_state.assert_called_once()
                assert os.path.realpath(mock_save_state.call_args.args[1]) == os.path.realpath(worktree_path)

            finally:
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)


class TestSelectIssueFileGeneration:
    """Test that file generation respects worktree path."""

    def test_spec_files_generated_in_worktree(self):
        """
        When Select Issue creates spec.md, plan.md, sbe.md,
        they should be created in worktree/docs/features/, not main repo.
        """
        # This test will be implemented when we fix the file generation in Select Issue
        # Currently marked as expected failure until implemented
        pytest.skip("TODO: Implement after fixing git operations path")
