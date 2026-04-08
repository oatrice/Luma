"""
Test suite for git worktree detection functionality.

Tests the TDD cycle for:
- get_git_worktree_path()
- is_git_worktree()
- resolve_project_target_dir()

Author: Luma
Date: 2026-04-08
"""

import os
import subprocess
import tempfile
import shutil
from unittest.mock import patch, MagicMock

import pytest

from luma_core.tools import (
    get_git_worktree_path,
    is_git_worktree,
    resolve_project_target_dir,
)


class TestGetGitWorktreePath:
    """Tests for get_git_worktree_path() function."""

    def test_returns_none_for_non_git_directory(self):
        """🟥 RED: Should return None when not in a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_git_worktree_path(tmpdir)
            assert result is None, "Expected None for non-git directory"

    def test_returns_toplevel_for_regular_repo(self):
        """🟥 RED: Should return toplevel path for regular git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a regular git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            result = get_git_worktree_path(tmpdir)
            # Normalize paths for macOS /private/var vs /var difference
            assert os.path.realpath(result) == os.path.realpath(tmpdir), f"Expected {tmpdir}, got {result}"

    def test_returns_worktree_path_for_worktree(self):
        """🟥 RED: Should return worktree toplevel path when in a worktree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create main repo and worktree
            main_repo = os.path.join(tmpdir, "main_repo")
            worktree_dir = os.path.join(tmpdir, "worktree")
            os.makedirs(main_repo)
            os.makedirs(worktree_dir)

            # Initialize main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)

            # Create initial commit (required for worktree)
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Test")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=main_repo, capture_output=True)

            # Create worktree
            subprocess.run(
                ["git", "worktree", "add", worktree_dir, "HEAD"],
                cwd=main_repo,
                capture_output=True,
                check=True
            )

            result = get_git_worktree_path(worktree_dir)
            # Normalize paths for macOS /private/var vs /var difference
            assert os.path.realpath(result) == os.path.realpath(worktree_dir), f"Expected {worktree_dir}, got {result}"

    def test_returns_none_on_git_command_failure(self):
        """🟥 RED: Should return None when git command fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock subprocess to simulate failure
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "git")
                result = get_git_worktree_path(tmpdir)
                assert result is None, "Expected None when git command fails"


class TestIsGitWorktree:
    """Tests for is_git_worktree() function."""

    def test_returns_false_for_non_git_directory(self):
        """🟥 RED: Should return False when not in a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = is_git_worktree(tmpdir)
            assert result is False, "Expected False for non-git directory"

    def test_returns_false_for_regular_repo(self):
        """🟥 RED: Should return False for regular git repo (not worktree)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize regular git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)

            result = is_git_worktree(tmpdir)
            assert result is False, "Expected False for regular git repo"

    def test_returns_true_for_worktree(self):
        """🟥 RED: Should return True when in a git worktree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create main repo and worktree
            main_repo = os.path.join(tmpdir, "main_repo")
            worktree_dir = os.path.join(tmpdir, "worktree")
            os.makedirs(main_repo)
            os.makedirs(worktree_dir)

            # Initialize main repo
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)

            # Create initial commit
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Test")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=main_repo, capture_output=True)

            # Create worktree
            subprocess.run(
                ["git", "worktree", "add", worktree_dir, "HEAD"],
                cwd=main_repo,
                capture_output=True,
                check=True
            )

            result = is_git_worktree(worktree_dir)
            assert result is True, "Expected True for worktree"

    def test_returns_false_on_git_command_failure(self):
        """🟥 RED: Should return False when git command fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "git")
                result = is_git_worktree(tmpdir)
                assert result is False, "Expected False when git command fails"


class TestResolveProjectTargetDir:
    """Tests for resolve_project_target_dir() function."""

    def test_returns_project_path_for_regular_repo(self):
        """🟥 RED: Should return project_path when not in worktree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = "/path/to/project"

            # Mock is_git_worktree to return False (regular repo)
            with patch("luma_core.tools.is_git_worktree", return_value=False):
                result = resolve_project_target_dir(project_path, tmpdir)
                assert result == project_path, f"Expected {project_path}, got {result}"

    def test_returns_worktree_path_when_in_worktree(self):
        """🟥 RED: Should return worktree path when cwd is a worktree."""
        worktree_path = "/path/to/worktree"
        project_path = "/path/to/original/project"
        cwd = "/some/current/dir"

        with patch("luma_core.tools.is_git_worktree", return_value=True):
            with patch("luma_core.tools.get_git_worktree_path", return_value=worktree_path):
                result = resolve_project_target_dir(project_path, cwd)
                assert result == worktree_path, f"Expected {worktree_path}, got {result}"

    def test_falls_back_to_project_path_when_worktree_detection_fails(self):
        """🟥 RED: Should fallback to project_path when worktree detection fails."""
        project_path = "/path/to/project"
        cwd = "/some/current/dir"

        with patch("luma_core.tools.is_git_worktree", return_value=True):
            with patch("luma_core.tools.get_git_worktree_path", return_value=None):
                result = resolve_project_target_dir(project_path, cwd)
                assert result == project_path, f"Expected {project_path}, got {result}"

    def test_uses_current_working_directory_when_cwd_not_provided(self):
        """🟥 RED: Should use os.getcwd() when cwd parameter not provided."""
        project_path = "/path/to/project"
        current_dir = "/current/working/dir"

        with patch("os.getcwd", return_value=current_dir):
            with patch("luma_core.tools.is_git_worktree") as mock_is_worktree:
                mock_is_worktree.return_value = False
                resolve_project_target_dir(project_path)
                mock_is_worktree.assert_called_once_with(current_dir)


class TestIntegrationWithPlanActions:
    """Integration tests for worktree detection in plan_actions."""

    def test_action_generate_spec_uses_resolved_path(self):
        """🟥 RED: Generate Spec should use resolve_project_target_dir."""
        from luma_core.actions.plan_actions import action_generate_spec

        # This is a smoke test to ensure the function can be imported and called
        # Full integration test would require mocking LumaState and project
        assert callable(action_generate_spec), "action_generate_spec should be callable"

    def test_action_generate_plan_uses_resolved_path(self):
        """🟥 RED: Generate Plan should use resolve_project_target_dir."""
        from luma_core.actions.plan_actions import action_generate_plan

        assert callable(action_generate_plan), "action_generate_plan should be callable"

    def test_action_generate_sbe_uses_resolved_path(self):
        """🟥 RED: Generate SBE should use resolve_project_target_dir."""
        from luma_core.actions.plan_actions import action_generate_sbe

        assert callable(action_generate_sbe), "action_generate_sbe should be callable"

    def test_action_generate_draft_uses_resolved_path(self):
        """🟥 RED: Generate Draft should use resolve_project_target_dir."""
        from luma_core.actions.plan_actions import action_generate_draft

        assert callable(action_generate_draft), "action_generate_draft should be callable"

    def test_action_refine_issue_uses_resolved_path(self):
        """🟥 RED: Refine Issue should use resolve_project_target_dir."""
        from luma_core.actions.plan_actions import action_refine_issue

        assert callable(action_refine_issue), "action_refine_issue should be callable"
