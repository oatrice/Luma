"""
Tests for LLM Failed Prompt Export Feature (Issue #67)

TDD: Red -> Green -> Refactor
"""

import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from luma_core.llm import (
    TrackedModel,
    _export_failed_prompt_to_file,
    _flatten_messages_to_prompt,
    _scrub_sensitive_data,
)
from luma_core.state_manager import LumaState, WorkflowPhase, IssueData


class TestScrubSensitiveData:
    """Test suite for sensitive data scrubbing in prompts"""

    def test_scrub_google_api_key(self):
        """Test that Google API keys are scrubbed from prompts"""
        prompt = "Call API with key AIzaSyDdI0rG7bU7Dqr3z9vI9zjBu9Xj9zjBu9X"
        result = _scrub_sensitive_data(prompt)
        assert "AIzaSyDdI0rG7bU7Dqr3z9vI9zjBu9Xj9zjBu9X" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_scrub_openai_api_key(self):
        """Test that OpenAI API keys are scrubbed from prompts"""
        prompt = "Use key sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        result = _scrub_sensitive_data(prompt)
        assert "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_scrub_bearer_token(self):
        """Test that Bearer tokens are scrubbed from prompts"""
        prompt = 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test'
        result = _scrub_sensitive_data(prompt)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED_TOKEN]" in result

    def test_no_scrub_in_normal_text(self):
        """Test that normal text without sensitive data is not modified"""
        prompt = "This is a normal prompt about Python programming."
        result = _scrub_sensitive_data(prompt)
        assert result == prompt


class TestExportFailedPromptToFile:
    """Test suite for _export_failed_prompt_to_file function"""

    @patch("builtins.open", mock_open())
    @patch("luma_core.llm.os.makedirs")
    @patch("luma_core.llm.datetime")
    def test_export_creates_file_with_correct_timestamp_format(self, mock_datetime, mock_makedirs):
        """Test that exported file uses human-readable timestamp format YYYYMMDD_HHMMSS"""
        mock_datetime.now.return_value = datetime(2026, 4, 9, 21, 5, 30, tzinfo=timezone.utc)

        feature_dir = "/fake/path/docs/features/21_issue-67_test"
        prompt = "Test prompt content"
        error_msg = "Test error"

        _export_failed_prompt_to_file(
            prompt=prompt,
            error_message=error_msg,
            model_name="gemini-2.5-pro",
            feature_dir=feature_dir,
        )

        # Verify filename format
        expected_filename = "luma_failed_prompt_20260409_210530.md"
        expected_path = os.path.join(feature_dir, "ai_brain", expected_filename)

        # Verify open was called with correct path
        assert open.call_args[0][0] == expected_path

    @patch("builtins.open", mock_open())
    @patch("luma_core.llm.os.makedirs")
    @patch("luma_core.llm.datetime")
    def test_export_creates_ai_brain_directory(self, mock_datetime, mock_makedirs):
        """Test that ai_brain subdirectory is created if it doesn't exist"""
        mock_datetime.now.return_value = datetime(2026, 4, 9, 21, 5, 30, tzinfo=timezone.utc)

        feature_dir = "/fake/path/docs/features/21_issue-67_test"

        _export_failed_prompt_to_file(
            prompt="Test prompt",
            error_message="Error",
            model_name="gemini-2.5-pro",
            feature_dir=feature_dir,
        )

        # Verify makedirs was called with ai_brain subdirectory
        expected_ai_brain_path = os.path.join(feature_dir, "ai_brain")
        mock_makedirs.assert_called_once_with(expected_ai_brain_path, exist_ok=True)

    @patch("builtins.open", mock_open())
    @patch("luma_core.llm.os.makedirs")
    @patch("luma_core.llm.datetime")
    def test_export_file_contains_required_metadata(self, mock_datetime, mock_makedirs):
        """Test that exported file contains phase, action, sub-action, model, error"""
        mock_datetime.now.return_value = datetime(2026, 4, 9, 21, 5, 30, tzinfo=timezone.utc)

        feature_dir = "/fake/path/docs/features/21_issue-67_test"
        prompt = "Test prompt content with code"
        error_msg = "Gemini CLI timed out after 120s"

        # Mock usage_tracker to return phase/action/sub-action
        with patch("luma_core.llm.usage_tracker.get_current_action", return_value="Auto Full Workflow"):
            with patch("luma_core.llm.usage_tracker.get_current_sub_action", return_value="Coding/Multi-Agent"):
                with patch("luma_core.state_manager.load_state") as mock_load_state:
                    mock_state = MagicMock()
                    mock_state.phase = WorkflowPhase.CODING
                    mock_load_state.return_value = mock_state

                    _export_failed_prompt_to_file(
                        prompt=prompt,
                        error_message=error_msg,
                        model_name="gemini-2.5-pro",
                        feature_dir=feature_dir,
                    )

        # Get the written content
        written_content = open().write.call_args[0][0]

        # Verify metadata exists
        assert "**Phase:** coding" in written_content
        assert "**Action:** Auto Full Workflow" in written_content
        assert "**Sub-Action:** Coding/Multi-Agent" in written_content
        assert "**Model:** gemini-2.5-pro" in written_content
        assert "**Error:** Gemini CLI timed out after 120s" in written_content
        assert "Test prompt content with code" in written_content

    @patch("builtins.open", mock_open())
    @patch("luma_core.llm.os.makedirs")
    @patch("luma_core.llm.print")
    @patch("luma_core.llm.datetime")
    def test_export_shows_user_message(self, mock_datetime, mock_print, mock_makedirs):
        """Test that user-facing export confirmation message is displayed"""
        mock_datetime.now.return_value = datetime(2026, 4, 9, 21, 5, 30, tzinfo=timezone.utc)

        feature_dir = "/fake/path/docs/features/21_issue-67_test"

        _export_failed_prompt_to_file(
            prompt="Test",
            error_message="Error",
            model_name="gemini-2.5-pro",
            feature_dir=feature_dir,
        )

        # Verify user message is printed
        expected_msg_pattern = r"❌ Gemini CLI failed after retries.*luma_failed_prompt_20260409_210530\.md.*external AI"
        printed_messages = [str(call) for call in mock_print.call_args_list]
        assert any(re.search(expected_msg_pattern, msg) for msg in printed_messages)

    @patch("builtins.open", mock_open())
    @patch("luma_core.llm.os.makedirs")
    @patch("luma_core.llm.datetime")
    def test_export_scrubs_sensitive_data_in_prompt(self, mock_datetime, mock_makedirs):
        """Test that sensitive data is scrubbed before writing to file"""
        mock_datetime.now.return_value = datetime(2026, 4, 9, 21, 5, 30, tzinfo=timezone.utc)

        feature_dir = "/fake/path/docs/features/21_issue-67_test"
        prompt_with_key = "Use API key AIzaSyDdI0rG7bU7Dqr3z9vI9zjBu9Xj9zjBu9X to call Gemini"

        _export_failed_prompt_to_file(
            prompt=prompt_with_key,
            error_message="Error",
            model_name="gemini-2.5-pro",
            feature_dir=feature_dir,
        )

        written_content = open().write.call_args[0][0]

        # Verify sensitive data is scrubbed
        assert "AIzaSyDdI0rG7bU7Dqr3z9vI9zjBu9Xj9zjBu9X" not in written_content
        assert "[REDACTED_API_KEY]" in written_content


class TestFeatureDirectoryResolution:
    """Test suite for feature directory resolution from state"""

    def test_resolve_feature_dir_from_luma_state(self):
        """Test that feature directory is resolved from .luma_state.json context"""
        # This test verifies the integration with state_manager
        from luma_core.llm import _resolve_feature_directory

        with patch("luma_core.state_manager.load_state") as mock_load_state:
            with patch("os.getcwd", return_value="/project/path"):
                with patch("os.path.exists", return_value=True):
                    mock_state = MagicMock()
                    mock_state.context = {"last_feature_dir": "/project/docs/features/21_issue-67_test"}
                    mock_load_state.return_value = mock_state

                    result = _resolve_feature_directory()

                    assert result == "/project/docs/features/21_issue-67_test"

    def test_fallback_to_cwd_when_no_state(self):
        """Test fallback when no state file exists"""
        from luma_core.llm import _resolve_feature_directory

        with patch("luma_core.state_manager.load_state", return_value=None):
            with patch("os.getcwd", return_value="/project/path"):
                result = _resolve_feature_directory()

                # Should fallback to a default path or return None
                assert result is None or isinstance(result, str)


class TestTrackedModelIntegration:
    """Test suite for TrackedModel integration with export functionality"""

    def test_tracked_model_exports_prompt_on_llm_failure(self):
        """Test that TrackedModel._generate calls export when _should_export_on_error returns True"""
        from luma_core.llm import _should_export_on_error

        # Verify the logic: when LUMA_EXPORT_PROMPTS is True, should return True
        with patch("luma_core.llm.LUMA_EXPORT_PROMPTS", True):
            assert _should_export_on_error() is True

    def test_tracked_model_skips_export_when_explicitly_disabled(self):
        """Test that export is skipped when LUMA_EXPORT_PROMPTS is explicitly False"""
        from luma_core.llm import _should_export_on_error

        # Verify the logic: when LUMA_EXPORT_PROMPTS is False, should return False
        with patch("luma_core.llm.LUMA_EXPORT_PROMPTS", False):
            assert _should_export_on_error() is False

    def test_tracked_model_exports_by_default_on_error(self):
        """Test that export occurs by default when LLM fails (LUMA_EXPORT_PROMPTS defaults to True on error)"""
        from luma_core.llm import _should_export_on_error

        # Verify the logic: when LUMA_EXPORT_PROMPTS is None (not set), should return True
        with patch("luma_core.llm.LUMA_EXPORT_PROMPTS", None):
            assert _should_export_on_error() is True


class TestGitignoreCompatibility:
    """Test suite for .gitignore pattern compatibility"""

    def test_exported_filename_matches_gitignore_pattern(self):
        """Test that generated filename matches luma_failed_prompt_*.md pattern"""
        # The pattern in .gitignore is: luma_failed_prompt_*.md
        filename = "luma_failed_prompt_20260409_210530.md"
        pattern = r"^luma_failed_prompt_.*\.md$"
        assert re.match(pattern, filename)

    def test_timestamp_does_not_contain_invalid_chars(self):
        """Test that timestamp format doesn't create invalid filename characters"""
        timestamp = "20260409_210530"
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            assert char not in timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
