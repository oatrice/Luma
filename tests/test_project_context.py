"""
Tests for project_context.py — TDD Red Phase
"""
import os
from pathlib import Path

import pytest


class TestLoadProjectContext:
    """Test load_project_context() helper."""

    def test_returns_dict_with_required_keys(self, tmp_path):
        """load_project_context should return dict with stack_summary and agent_rules."""
        from luma_core.project_context import load_project_context

        result = load_project_context(str(tmp_path))

        assert isinstance(result, dict)
        assert "stack_summary" in result
        assert "agent_rules" in result

    def test_returns_defaults_when_no_files(self, tmp_path):
        """Should not crash and return empty strings when no docs exist."""
        from luma_core.project_context import load_project_context

        result = load_project_context(str(tmp_path))

        assert result["stack_summary"] == ""
        assert result["agent_rules"] == ""

    def test_reads_readme_tech_stack(self, tmp_path):
        """Should extract content from README.md."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "# My Project

## Tech Stack
- **Framework**: Gin
- **Language**: Go
",
            encoding="utf-8",
        )

        from luma_core.project_context import load_project_context

        result = load_project_context(str(tmp_path))

        assert "Gin" in result["stack_summary"] or "Go" in result["stack_summary"]

    def test_reads_agents_md(self, tmp_path):
        """Should extract content from AGENTS.md when present."""
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text(
            "# AGENTS.md

## Repo Map
- Backend: oatrice/TheMiddleWay-Backend
",
            encoding="utf-8",
        )

        from luma_core.project_context import load_project_context

        result = load_project_context(str(tmp_path))

        assert "TheMiddleWay-Backend" in result["agent_rules"]

    def test_reads_gemini_md_as_fallback(self, tmp_path):
        """Should read GEMINI.md if AGENTS.md is absent."""
        gemini_md = tmp_path / "GEMINI.md"
        gemini_md.write_text(
            "# GEMINI.md

Project Name: `The Middle Way`
",
            encoding="utf-8",
        )

        from luma_core.project_context import load_project_context

        result = load_project_context(str(tmp_path))

        assert "The Middle Way" in result["agent_rules"]

    def test_prefers_agents_md_over_gemini_md(self, tmp_path):
        """If both AGENTS.md and GEMINI.md exist, AGENTS.md should take priority."""
        (tmp_path / "AGENTS.md").write_text("AGENTS content", encoding="utf-8")
        (tmp_path / "GEMINI.md").write_text("GEMINI content", encoding="utf-8")

        from luma_core.project_context import load_project_context

        result = load_project_context(str(tmp_path))

        assert "AGENTS content" in result["agent_rules"]
        assert "GEMINI content" not in result["agent_rules"]

    def test_truncates_very_long_readme(self, tmp_path):
        """Should truncate README to avoid overwhelming the LLM context."""
        readme = tmp_path / "README.md"
        readme.write_text("# Big Readme
" + "x" * 20000, encoding="utf-8")

        from luma_core.project_context import load_project_context

        result = load_project_context(str(tmp_path))

        # Should be truncated to a reasonable size
        assert len(result["stack_summary"]) <= 6000

    def test_does_not_crash_on_unreadable_file(self, tmp_path):
        """Should handle IOError gracefully."""
        from luma_core.project_context import load_project_context

        # Pass a directory that doesn't contain these files, should not raise
        result = load_project_context("/nonexistent/path/xyz")

        assert result["stack_summary"] == ""
        assert result["agent_rules"] == ""


class TestBuildContextBlock:
    """Test build_context_block() that formats context for LLM prompt injection."""

    def test_returns_empty_string_when_no_context(self):
        """Should return empty string if both fields are empty."""
        from luma_core.project_context import build_context_block

        result = build_context_block({"stack_summary": "", "agent_rules": ""})

        assert result == ""

    def test_formats_stack_summary(self):
        """Should include stack_summary in formatted block."""
        from luma_core.project_context import build_context_block

        result = build_context_block(
            {"stack_summary": "Go, Gin, GORM", "agent_rules": ""}
        )

        assert "Go, Gin, GORM" in result

    def test_formats_agent_rules(self):
        """Should include agent_rules in formatted block."""
        from luma_core.project_context import build_context_block

        result = build_context_block(
            {"stack_summary": "", "agent_rules": "Backend: oatrice/TheMiddleWay-Backend"}
        )

        assert "oatrice/TheMiddleWay-Backend" in result

    def test_block_has_section_headers(self):
        """Result should have recognizable section headers for LLM."""
        from luma_core.project_context import build_context_block

        result = build_context_block(
            {"stack_summary": "Go", "agent_rules": "Some rules"}
        )

        assert "Tech Stack" in result or "PROJECT CONTEXT" in result


class TestGetProjectRootDir:
    """Tests for get_project_root_dir function."""

    @pytest.fixture
    def setup_git_repo(self, tmp_path):
        """Fixture to set up a basic Git repository."""
        repo_path = tmp_path / "main_repo"
        repo_path.mkdir()
        os.chdir(repo_path)
        os.system("git init -b main > /dev/null 2>&1")
        (repo_path / "file.txt").write_text("content")
        os.system("git add . > /dev/null 2>&1")
        os.system("git commit -m 'Initial commit' > /dev/null 2>&1")
        return repo_path

    @pytest.fixture
    def setup_git_worktree(self, setup_git_repo, tmp_path):
        """Fixture to set up a Git worktree."""
        main_repo_path = setup_git_repo
        worktree_path = tmp_path / "worktree_repo"
        os.chdir(main_repo_path)
        os.system(f"git worktree add {worktree_path} feature-branch > /dev/null 2>&1")
        os.chdir(worktree_path)
        return worktree_path

    def test_returns_main_repo_root_from_main_repo(self, setup_git_repo):
        """Should return the main repository root when called from main repo."""
        from luma_core.project_context import get_project_root_dir
        assert get_project_root_dir() == setup_git_repo

    def test_returns_main_repo_root_from_nested_dir_in_main_repo(self, setup_git_repo):
        """Should return the main repository root when called from a nested directory."""
        from luma_core.project_context import get_project_root_dir
        nested_path = setup_git_repo / "nested"
        nested_path.mkdir()
        os.chdir(nested_path)
        assert get_project_root_dir() == setup_git_repo

    def test_returns_worktree_root_from_worktree(self, setup_git_worktree):
        """Should return the worktree root when called from a worktree."""
        from luma_core.project_context import get_project_root_dir
        assert get_project_root_dir() == setup_git_worktree

    def test_returns_worktree_root_from_nested_dir_in_worktree(self, setup_git_worktree):
        """Should return the worktree root when called from a nested directory in a worktree."""
        from luma_core.project_context import get_project_root_dir
        nested_path = setup_git_worktree / "nested"
        nested_path.mkdir()
        os.chdir(nested_path)
        assert get_project_root_dir() == setup_git_worktree

    def test_returns_current_path_if_not_git_repo(self, tmp_path):
        """Should return the current working directory if not a Git repository."""
        from luma_core.project_context import get_project_root_dir
        non_git_path = tmp_path / "non_git_dir"
        non_git_path.mkdir()
        os.chdir(non_git_path)
        assert get_project_root_dir() == non_git_path

    def test_get_project_root_dir_explicit_path_non_git(self, tmp_path):
        """Should return the explicit path if it's not a git repo."""
        from luma_core.project_context import get_project_root_dir
        explicit_path = tmp_path / "some_dir"
        explicit_path.mkdir()
        assert get_project_root_dir(explicit_path) == explicit_path

    def test_get_project_root_dir_explicit_path_main_repo(self, setup_git_repo):
        """Should return the main repo root when explicit path is main repo."""
        from luma_core.project_context import get_project_root_dir
        assert get_project_root_dir(setup_git_repo) == setup_git_repo

    def test_get_project_root_dir_explicit_path_worktree(self, setup_git_worktree):
        """Should return the worktree root when explicit path is worktree."""
        from luma_core.project_context import get_project_root_dir
        assert get_project_root_dir(setup_git_worktree) == setup_git_worktree

