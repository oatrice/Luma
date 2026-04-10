"""Tests for LLM timeout and retry configuration options."""
import os
import pytest
import subprocess
import tempfile
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage
from luma_core.llm import GeminiCLIModel, get_llm, MODEL_TIMEOUTS


class TestTimeoutScaleConfig:
    """Test LUMA_LLM_TIMEOUT_SCALE configuration."""

    @patch("subprocess.Popen")
    def test_timeout_scale_reduces_model_timeout(self, mock_popen):
        """When LUMA_LLM_TIMEOUT_SCALE=0.5, timeout should be halved."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("response", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # gemini-2.5-pro normally has 120s timeout
        base_timeout = MODEL_TIMEOUTS["gemini-2.5-pro"]  # 120

        with patch("luma_core.llm.LUMA_LLM_TIMEOUT_SCALE", 0.5):
            with patch("luma_core.llm.usage_tracker.record_llm_event"):
                with patch("luma_core.config.GOOGLE_API_KEYS", []):
                    with patch("luma_core.config.GEMINI_CLI_PROFILES", []):
                        model = GeminiCLIModel(model="gemini-2.5-pro")
                        model.invoke([HumanMessage(content="Hello")])

        kwargs = mock_process.communicate.call_args[1]
        # 120 * 0.5 = 60
        expected_timeout = int(base_timeout * 0.5)
        assert kwargs.get("timeout") == expected_timeout

    @patch("subprocess.Popen")
    def test_timeout_scale_minimum_10_seconds(self, mock_popen):
        """Timeout should not go below 10 seconds to prevent immediate failures."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("response", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        with patch("luma_core.llm.LUMA_LLM_TIMEOUT_SCALE", 0.01):
            with patch("luma_core.llm.usage_tracker.record_llm_event"):
                with patch("luma_core.config.GOOGLE_API_KEYS", []):
                    with patch("luma_core.config.GEMINI_CLI_PROFILES", []):
                        model = GeminiCLIModel(model="gemini-2.5-pro")
                        model.invoke([HumanMessage(content="Hello")])

        kwargs = mock_process.communicate.call_args[1]
        # Even with 0.01 scale, should be at least 10 seconds
        assert kwargs.get("timeout") >= 10


class TestMaxRetriesConfig:
    """Test LUMA_MAX_LLM_RETRIES configuration."""

    @patch("subprocess.Popen")
    @patch("time.sleep")
    @patch("builtins.print")
    def test_max_retries_limits_attempts(self, mock_print, mock_sleep, mock_popen):
        """When LUMA_MAX_LLM_RETRIES=1, should only try 1 attempt as shown in logs."""
        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(
            cmd=["gemini"], timeout=60
        )
        mock_popen.return_value = mock_process

        with patch("luma_core.config.GOOGLE_API_KEYS", []):
            with patch("luma_core.config.GEMINI_CLI_PROFILES", []):
                with patch("luma_core.llm.LUMA_MAX_LLM_RETRIES", 1):
                    model = GeminiCLIModel(model="gemini-2.5-flash")
                    with pytest.raises(RuntimeError):
                        model.invoke([HumanMessage(content="Hello")])

        # Verify the log message shows 1/1 attempts
        printed = " ".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        assert "Attempt 1/1" in printed

    @patch("subprocess.Popen")
    @patch("builtins.print")
    def test_zero_max_retries_uses_single_attempt(self, mock_print, mock_popen):
        """When LUMA_MAX_LLM_RETRIES=0, should still try at least once (min 1)."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("response", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        with patch("luma_core.llm.LUMA_MAX_LLM_RETRIES", 0):
            with patch("luma_core.llm.usage_tracker.record_llm_event"):
                with patch("luma_core.config.GOOGLE_API_KEYS", []):
                    with patch("luma_core.config.GEMINI_CLI_PROFILES", []):
                        model = GeminiCLIModel(model="gemini-2.5-flash")
                        model.invoke([HumanMessage(content="Hello")])

        # Should have logged at least 1 attempt (min 1 is enforced)
        printed = " ".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        assert "Attempt:" in printed and "1/1" in printed


class TestPromptExportMode:
    """Test LUMA_EXPORT_PROMPTS mode - saves prompts instead of calling LLM."""

    @patch("luma_core.llm.PromptExportModel")
    def test_export_prompts_returns_prompt_export_model(self, mock_export_class):
        """When LUMA_EXPORT_PROMPTS=true, get_llm should return PromptExportModel."""
        mock_instance = MagicMock()
        mock_export_class.return_value = mock_instance

        with patch("luma_core.config.LLM_PROVIDER", "gemini-cli"):
            with patch("luma_core.llm.LUMA_EXPORT_PROMPTS", True):
                get_llm()

        mock_export_class.assert_called_once()

    def test_prompt_export_model_saves_to_file(self):
        """PromptExportModel should save prompt to .luma/prompts/ directory."""
        from luma_core.llm import PromptExportModel

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(os, "getcwd", return_value=tmpdir):
                model = PromptExportModel(wrapped_model_name="gemini-2.5-pro")
                messages = [HumanMessage(content="Test prompt content")]

                model.invoke(messages)

                # Check that a .md file was created in the prompts directory
                prompts_dir = os.path.join(tmpdir, ".luma/prompts")
                assert os.path.exists(prompts_dir)
                files = os.listdir(prompts_dir)
                assert len(files) == 1
                assert files[0].endswith(".md")

    def test_prompt_export_model_returns_placeholder_response(self):
        """PromptExportModel should return a placeholder response with file path."""
        from luma_core.llm import PromptExportModel

        with patch("builtins.open", MagicMock()):
            with patch("os.makedirs"):
                model = PromptExportModel(wrapped_model_name="gemini-2.5-pro")
                messages = [HumanMessage(content="Test prompt")]

                result = model.invoke(messages)

                # Should return placeholder indicating where prompt was saved
                assert "[PROMPT EXPORTED]" in result.content
                assert ".luma/prompts/" in result.content


class TestConfigVariables:
    """Test that config variables are properly defined."""

    def test_luma_llm_timeout_scale_exists_in_config(self):
        """LUMA_LLM_TIMEOUT_SCALE should be defined in config module."""
        from luma_core import config
        assert hasattr(config, "LUMA_LLM_TIMEOUT_SCALE")
        assert isinstance(config.LUMA_LLM_TIMEOUT_SCALE, (int, float))

    def test_luma_max_llm_retries_exists_in_config(self):
        """LUMA_MAX_LLM_RETRIES should be defined in config module."""
        from luma_core import config
        assert hasattr(config, "LUMA_MAX_LLM_RETRIES")
        # Can be None (default) or int when set
        assert config.LUMA_MAX_LLM_RETRIES is None or isinstance(config.LUMA_MAX_LLM_RETRIES, int)

    def test_luma_export_prompts_exists_in_config(self):
        """LUMA_EXPORT_PROMPTS should be defined in config module."""
        from luma_core import config
        assert hasattr(config, "LUMA_EXPORT_PROMPTS")
        # Can be None (default - auto-export on error) or bool when explicitly set
        assert config.LUMA_EXPORT_PROMPTS is None or isinstance(config.LUMA_EXPORT_PROMPTS, bool)
