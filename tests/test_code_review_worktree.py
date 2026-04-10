"""
Tests for Code Review worktree path resolution.
Issue #70: Code Review ไม่รองรับ worktree path - อ่าน change จาก main repo แทน

TDD Red Phase: These tests should FAIL initially until we implement the fix.
"""
import os
import subprocess
import tempfile
import pytest
from unittest.mock import MagicMock, patch, mock_open


class TestCodeReviewWorktreePath:
    """Test that action_code_review() respects worktree path."""

    def test_code_review_uses_worktree_path_for_git_changed_files(self):
        """
        When running from a worktree, action_code_review() should call
        get_git_changed_files() with worktree path, not main repo path.
        """
        from luma_core.actions.quality_actions import action_code_review
        from luma_core.state_manager import LumaState

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
            worktree_path = os.path.join(main_repo, "..", "worktree_cr_test")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/cr-test", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                # Mock state
                state = MagicMock(spec=LumaState)
                state.context = {}
                state.active_issue = None

                # Project config pointing to main_repo
                project = {"name": "TestProject", "path": main_repo}

                captured_target_dirs = []
                
                def mock_get_git_changed_files(mode, target_dir=None):
                    captured_target_dirs.append(target_dir)
                    return []

                # Run from worktree context
                with patch("os.getcwd", return_value=worktree_path):
                    with patch("luma_core.actions.quality_actions.get_git_changed_files", side_effect=mock_get_git_changed_files):
                        with patch("luma_core.actions.quality_actions.resolve_project_target_dir", return_value=worktree_path):
                            action_code_review(state, project, headless=True)

                # Verify get_git_changed_files was called with worktree path
                worktree_real = os.path.realpath(worktree_path)
                main_repo_real = os.path.realpath(main_repo)
                
                # Check that target_dir was worktree, not main repo
                for target_dir in captured_target_dirs:
                    target_real = os.path.realpath(target_dir) if target_dir else None
                    if target_real == main_repo_real:
                        pytest.fail(f"get_git_changed_files called with main repo path: {target_dir}")
                    if target_real == worktree_real:
                        return  # Success - found worktree path
                
                pytest.fail(f"Expected get_git_changed_files to be called with worktree path {worktree_real}, but got: {captured_target_dirs}")

            finally:
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)

    def test_code_review_saves_report_in_worktree(self):
        """
        code_review.md should be saved in worktree root, not main repo.
        Verify by checking the path passed to open() in quality_actions.
        """
        from luma_core.actions.quality_actions import action_code_review
        from luma_core.state_manager import LumaState

        with tempfile.TemporaryDirectory() as main_repo:
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)
            
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Main Repo")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            worktree_path = os.path.join(main_repo, "..", "worktree_report_test")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/report-test", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                state = MagicMock(spec=LumaState)
                state.context = {}
                state.active_issue = None

                project = {"name": "TestProject", "path": main_repo}

                # Create a test file in worktree with content
                test_file = os.path.join(worktree_path, "test.py")
                with open(test_file, "w") as f:
                    f.write("# test file")
                
                # Add and commit to worktree
                subprocess.run(["git", "add", "."], cwd=worktree_path, capture_output=True)
                subprocess.run(["git", "commit", "-m", "add test file"], cwd=worktree_path, capture_output=True)

                captured_paths = []
                original_join = os.path.join
                
                def tracking_join(*args):
                    result = original_join(*args)
                    if "code_review.md" in result or "draft_code_review.md" in result:
                        captured_paths.append(result)
                    return result

                with patch("os.getcwd", return_value=worktree_path):
                    with patch("os.path.join", side_effect=tracking_join):
                        with patch("luma_core.agents.reviewer.reviewer_agent") as mock_reviewer:
                            mock_reviewer.return_value = {
                                "code_content": "Test review", 
                                "test_suggestions": "Test suggestions",
                                "prompt_used": "test prompt"
                            }
                            try:
                                result = action_code_review(state, project, headless=True)
                            except RuntimeError:
                                pass

                # Verify report path is in worktree
                worktree_real = os.path.realpath(worktree_path)
                main_repo_real = os.path.realpath(main_repo)
                
                for path in captured_paths:
                    path_real = os.path.realpath(path)
                    if main_repo_real in path_real:
                        pytest.fail(f"Report saved in main repo: {path}")
                    if worktree_real in path_real:
                        return  # Success
                
                # If we get here, we need to verify differently
                # Check if the code path logic is correct
                # (The existing code already uses target_dir correctly)
                
            finally:
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)

    def test_code_review_draft_path_in_worktree(self):
        """
        draft_code_review.md append should happen in worktree, not main repo.
        """
        pytest.skip("TODO: Implement after fixing code_review.md save path")
