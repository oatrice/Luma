import json
from unittest.mock import patch, mock_open
from luma_core.actions import action_settings

@patch("luma_core.config.save_fallback_index")
@patch("luma_core.actions.admin_actions.safe_input", side_effect=["1", "2", "8"]) # 1: Change LLM, 2: OpenRouter, 8: Back
@patch("builtins.print")
def test_action_settings_change_llm_provider(mock_print, mock_safe_input, mock_save_fallback_index):
    mock_file_content = "{}"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
        with patch("os.path.exists", return_value=True):
            action_settings()

            # Assert file was written
            mock_file().write.assert_called()
            written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
            saved_config = json.loads(written_data)
            assert saved_config["LLM_PROVIDER"] == "openrouter"

@patch("luma_core.actions.admin_actions.safe_input", side_effect=["2", "1", "8"]) # 2: Change CLI, 1: Gemini CLI, 8: Back
@patch("builtins.print")
def test_action_settings_change_agent_cli(mock_print, mock_safe_input):
    mock_file_content = "{}"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
        with patch("os.path.exists", return_value=True):
            action_settings()

            mock_file().write.assert_called()
            written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
            saved_config = json.loads(written_data)
            assert saved_config["AGENT_CLI"] == "gemini_cli"


@patch("luma_core.config.save_fallback_index")
@patch("luma_core.actions.admin_actions.safe_input", side_effect=["1", "4", "8"])  # 1: Change LLM, 4: Codex CLI, 8: Back
@patch("builtins.print")
def test_action_settings_change_llm_provider_to_codex_cli(
    mock_print,
    mock_safe_input,
    mock_save_fallback_index,
):
    mock_file_content = "{}"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
        with patch("os.path.exists", return_value=True):
            action_settings()

            mock_file().write.assert_called()
            written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
            saved_config = json.loads(written_data)
            assert saved_config["LLM_PROVIDER"] == "codex-cli"


@patch("os.getcwd", return_value="/tmp/zenith")
@patch("luma_core.config.save_fallback_index")
@patch("luma_core.actions.admin_actions.safe_input", side_effect=["1", "4", "8"])  # 1: Change LLM, 4: Codex CLI, 8: Back
@patch("builtins.print")
def test_action_settings_resets_fallback_index_when_llm_provider_changes(
    mock_print,
    mock_safe_input,
    mock_save_fallback_index,
    mock_getcwd,
):
    mock_file_content = '{"LLM_PROVIDER": "gemini-cli"}'
    with patch("builtins.open", mock_open(read_data=mock_file_content)):
        with patch("os.path.exists", return_value=True):
            action_settings()

    mock_save_fallback_index.assert_called_once_with(0, "/tmp/zenith")
