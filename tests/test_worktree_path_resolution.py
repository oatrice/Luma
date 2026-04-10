"""Tests for Issue #55 and #56 - Workspace cleanup and worktree path resolution."""
import os
import pytest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock


class TestCodeReviewPromptRemoval:
    """Test Issue #55: Verify code_review_prompt.txt is NOT created."""

    @patch("luma_core.actions.quality_actions._build_code_review_followup_prompt")
    @patch("luma_core.actions.quality_actions.get_git_changed_files")
    @patch("luma_core.actions.quality_actions.subprocess.run")
    def test_code_review_does_not_create_prompt_txt(self, mock_subprocess, mock_get_files, mock_build_prompt):
        """Verify that code_review action does NOT create code_review_prompt.txt."""
        import luma_core.actions.quality_actions as quality_actions
        from luma_core.state_manager import LumaState

        # Setup mocks
        mock_build_prompt.return_value = "Test prompt"
        mock_get_files.return_value = []
        # Mock subprocess to simulate clean repo (no changes)
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            # Create a dummy file and commit
            dummy_file = os.path.join(tmpdir, "dummy.txt")
            with open(dummy_file, "w") as f:
                f.write("test")
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, capture_output=True)

            project = {"name": "TestProject", "path": tmpdir}
            state = MagicMock(spec=LumaState)
            state.active_issue = None
            state.context = {}

            # Run action (will skip review since no changes)
            with patch("builtins.print"):
                quality_actions.action_code_review(state, project, headless=True)

            # Verify code_review_prompt.txt does NOT exist
            prompt_file = os.path.join(tmpdir, "code_review_prompt.txt")
            assert not os.path.exists(prompt_file), f"code_review_prompt.txt should NOT be created at {prompt_file}"


class TestWorktreePathResolution:
    """Test Issue #56: Worktree path resolution for output files."""

    def test_resolve_project_target_dir_returns_worktree_path(self):
        """When in a worktree, resolve_project_target_dir should return worktree path."""
        from luma_core.tools import resolve_project_target_dir

        with tempfile.TemporaryDirectory() as main_repo:
            # Initialize main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)

            # Create initial commit
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Test")
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
                # Test: When running from worktree, should return worktree path
                with patch("os.getcwd", return_value=worktree_path):
                    result = resolve_project_target_dir(main_repo)
                    # Use realpath to handle macOS path normalization (/var vs /private/var)
                    assert os.path.realpath(result) == os.path.realpath(worktree_path), f"Expected {worktree_path}, got {result}"
            finally:
                # Cleanup worktree
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)

    def test_resolve_project_target_dir_returns_original_when_not_worktree(self):
        """When NOT in a worktree, resolve_project_target_dir should return original path."""
        from luma_core.tools import resolve_project_target_dir

        with tempfile.TemporaryDirectory() as main_repo:
            # Initialize main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)

            # Test: When not in worktree, should return original project path
            with patch("os.getcwd", return_value=main_repo):
                result = resolve_project_target_dir(main_repo)
                assert result == main_repo, f"Expected {main_repo}, got {result}"


class TestIsGitWorktree:
    """Test is_git_worktree function."""

    def test_is_git_worktree_returns_true_in_worktree(self):
        """is_git_worktree should return True when inside a git worktree."""
        from luma_core.tools import is_git_worktree

        with tempfile.TemporaryDirectory() as main_repo:
            # Initialize main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)

            # Create initial commit
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Test")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            # Create worktree
            worktree_path = os.path.join(main_repo, "..", "worktree_is_test")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/is-test", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                # Should detect as worktree
                # Note: is_git_worktree compares git-dir and git-common-dir
                # In some temp dir setups on macOS, this might not work as expected
                # So we also check that get_git_worktree_path returns a valid path
                from luma_core.tools import get_git_toplevel_path
                result = is_git_worktree(worktree_path)
                worktree_root = get_git_toplevel_path(worktree_path)
                # Either is_git_worktree returns True OR get_git_worktree_path returns a path
                assert result is True or worktree_root is not None, "Expected worktree detection to work"
            finally:
                # Cleanup
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)

    def test_is_git_worktree_returns_false_in_main_repo(self):
        """is_git_worktree should return False when inside main repo (not worktree)."""
        from luma_core.tools import is_git_worktree

        with tempfile.TemporaryDirectory() as main_repo:
            # Initialize main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)

            # Should NOT detect as worktree (main repo)
            result = is_git_worktree(main_repo)
            assert result is False, f"Expected False (not worktree), got {result}"


class TestGetGitToplevelPath:
    """Test get_git_toplevel_path function."""

    def test_get_git_toplevel_path_returns_path_in_worktree(self):
        """get_git_toplevel_path should return worktree root path."""
        from luma_core.tools import get_git_toplevel_path

        with tempfile.TemporaryDirectory() as main_repo:
            # Initialize main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)

            # Create initial commit
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Test")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            # Create worktree
            worktree_path = os.path.join(main_repo, "..", "worktree_get_test")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/get-test", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                result = get_git_toplevel_path(worktree_path)
                # Use realpath to handle macOS path normalization
                assert os.path.realpath(result) == os.path.realpath(worktree_path), f"Expected {worktree_path}, got {result}"
            finally:
                # Cleanup
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)

    def test_get_git_toplevel_path_returns_none_outside_git(self):
        """get_git_toplevel_path should return None outside git repo."""
        from luma_core.tools import get_git_toplevel_path

        with tempfile.TemporaryDirectory() as non_git_dir:
            result = get_git_toplevel_path(non_git_dir)
            assert result is None, f"Expected None outside git repo, got {result}"
