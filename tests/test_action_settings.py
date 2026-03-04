import json
import pytest
from unittest.mock import patch, mock_open
from luma_core.actions import action_settings

@patch("builtins.input", side_effect=["1", "2", "3"]) # 1: Change LLM, 2: OpenRouter, 3: Back
@patch("builtins.print")
def test_action_settings_change_llm_provider(mock_print, mock_input):
    mock_file_content = "{}"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
        with patch("os.path.exists", return_value=True):
            action_settings()
            
            # Assert file was written
            mock_file().write.assert_called()
            written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
            saved_config = json.loads(written_data)
            assert saved_config["LLM_PROVIDER"] == "openrouter"

@patch("builtins.input", side_effect=["2", "1", "3"]) # 2: Change CLI, 1: Gemini CLI, 3: Back
@patch("builtins.print")
def test_action_settings_change_agent_cli(mock_print, mock_input):
    mock_file_content = "{}"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
        with patch("os.path.exists", return_value=True):
            action_settings()
            
            mock_file().write.assert_called()
            written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
            saved_config = json.loads(written_data)
            assert saved_config["AGENT_CLI"] == "gemini_cli"
