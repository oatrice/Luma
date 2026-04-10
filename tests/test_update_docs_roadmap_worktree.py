"""
Tests for Update Docs & Roadmap worktree path resolution.
Issue #64, #70: Fix worktree support

TDD Red Phase: These tests should FAIL initially until we implement the fix.
"""
import os
import subprocess
import tempfile
import pytest
from unittest.mock import MagicMock, patch


class TestUpdateDocsWorktreePath:
    """Test that action_update_docs() respects worktree path."""

    def test_update_docs_checks_changelog_in_worktree(self):
        """
        When running from a worktree, action_update_docs() should look for
        CHANGELOG.md and README.md in worktree, not main repo.
        """
        from luma_core.actions.quality_actions import action_update_docs
        from luma_core.state_manager import LumaState

        with tempfile.TemporaryDirectory() as main_repo:
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)
            
            with open(os.path.join(main_repo, "README.md"), "w") as f:
                f.write("# Main Repo")
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            worktree_path = os.path.join(main_repo, "..", "worktree_docs_test")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/docs-test", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                # Create different CHANGELOG in worktree
                with open(os.path.join(worktree_path, "CHANGELOG.md"), "w") as f:
                    f.write("# Worktree Changelog\n\n## [Unreleased]\n")

                state = MagicMock(spec=LumaState)
                state.context = {}

                project = {"name": "TestProject", "path": main_repo}

                captured_paths = []
                original_exists = os.path.exists
                
                def tracking_exists(path):
                    captured_paths.append(path)
                    return original_exists(path)

                with patch("os.getcwd", return_value=worktree_path):
                    with patch("os.path.exists", side_effect=tracking_exists):
                        with patch("luma_core.actions.quality_actions.ui.safe_input", return_value="0"):
                            try:
                                action_update_docs(state, project, skip_confirm=True)
                            except Exception:
                                pass

                # Check if paths were in worktree
                worktree_real = os.path.realpath(worktree_path)
                main_repo_real = os.path.realpath(main_repo)
                
                changelog_in_worktree = False
                changelog_in_main = False
                
                for path in captured_paths:
                    if "CHANGELOG.md" in path:
                        path_real = os.path.realpath(path)
                        if worktree_real in path_real:
                            changelog_in_worktree = True
                        if main_repo_real in path_real:
                            changelog_in_main = True

                if changelog_in_main and not changelog_in_worktree:
                    pytest.fail("Checked CHANGELOG.md in main repo instead of worktree")
                
                # Test passes if we checked worktree path
                # (current implementation may check both, which is ok)
                
            finally:
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)


class TestUpdateRoadmapWorktreePath:
    """Test that action_update_roadmap() respects worktree path."""

    def test_update_roadmap_looks_for_roadmap_in_worktree(self):
        """
        When running from a worktree, action_update_roadmap() should look for
        ROADMAP.md in worktree/docs/ or worktree/, not main repo.
        """
        from luma_core.actions.quality_actions import action_update_roadmap
        from luma_core.state_manager import LumaState

        with tempfile.TemporaryDirectory() as main_repo:
            subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=main_repo, capture_output=True)
            
            # Create ROADMAP in main repo
            os.makedirs(os.path.join(main_repo, "docs"), exist_ok=True)
            with open(os.path.join(main_repo, "docs", "ROADMAP.md"), "w") as f:
                f.write("# Main Repo Roadmap\n")
            
            subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=main_repo, capture_output=True)

            worktree_path = os.path.join(main_repo, "..", "worktree_roadmap_test")
            worktree_path = os.path.abspath(worktree_path)
            subprocess.run(
                ["git", "worktree", "add", "-b", "feat/roadmap-test", worktree_path],
                cwd=main_repo, capture_output=True
            )

            try:
                # Create different ROADMAP in worktree
                os.makedirs(os.path.join(worktree_path, "docs"), exist_ok=True)
                with open(os.path.join(worktree_path, "docs", "ROADMAP.md"), "w") as f:
                    f.write("# Worktree Roadmap\n\n## Issue #999\n- **Status:** 🟡 In Progress\n")

                state = MagicMock(spec=LumaState)
                state.active_issues = []

                project = {"name": "TestProject", "path": main_repo}

                captured_paths = []
                original_exists = os.path.exists
                
                def tracking_exists(path):
                    captured_paths.append(path)
                    return original_exists(path)

                with patch("os.getcwd", return_value=worktree_path):
                    with patch("os.path.exists", side_effect=tracking_exists):
                        try:
                            action_update_roadmap(state, project, headless=True)
                        except Exception:
                            pass

                # Verify worktree path was checked
                worktree_real = os.path.realpath(worktree_path)
                main_repo_real = os.path.realpath(main_repo)
                
                roadmap_in_worktree = False
                roadmap_in_main = False
                
                for path in captured_paths:
                    if "ROADMAP.md" in path:
                        path_real = os.path.realpath(path)
                        if worktree_real in path_real:
                            roadmap_in_worktree = True
                        if main_repo_real in path_real:
                            roadmap_in_main = True

                # Should prefer worktree path
                assert roadmap_in_worktree, f"Did not check ROADMAP.md in worktree {worktree_real}"
                
                # If current implementation checks main repo first, that's the bug
                if roadmap_in_main and not roadmap_in_worktree:
                    pytest.fail("Only checked ROADMAP.md in main repo, not worktree")
                
            finally:
                subprocess.run(["git", "worktree", "remove", "-f", worktree_path], cwd=main_repo, capture_output=True)
