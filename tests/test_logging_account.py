import pytest
from unittest.mock import MagicMock, patch
from luma_core.llm import TrackedModel, GeminiCLIModel, GeminiAPIModel, _mask_account, _resolve_model_info
from luma_core.credential_manager import CredentialManager
from langchain_core.messages import AIMessage

def test_mask_account_api_key():
    assert _mask_account("AIzaTestKey12345678") == "****5678"
    assert _mask_account("sk-TestKeyOpenAI1234") == "****1234"

def test_mask_account_profile():
    assert _mask_account("personal") == "personal"
    assert _mask_account("work") == "work"

def test_resolve_model_info_naming():
    # Test Gemini API naming
    api_model = GeminiAPIModel(model="gemini-2.5-pro")
    provider, _, _, _ = _resolve_model_info(api_model)
    assert provider == "gemini-api"
    
    # Test Gemini CLI naming
    cli_model = GeminiCLIModel(model="gemini-2.5-flash")
    provider, _, _, _ = _resolve_model_info(cli_model)
    assert provider == "gemini-cli"

@patch("luma_core.usage_tracker.record_llm_event")
@patch("luma_core.config.GOOGLE_API_KEYS", ["AIza_Key_1", "AIza_Key_2"])
@patch("luma_core.config.GEMINI_CLI_PROFILES", ["personal", "work"])
def test_isolated_pools(mock_record):
    # Reset all instances first
    CredentialManager.reset_all_instances()
    
    # 1. Test Gemini API (should only use API keys)
    api_model = GeminiAPIModel(model="gemini-2.5-pro")
    tracked_api = TrackedModel(model=api_model)
    
    # Mock ChatGoogleGenerativeAI instance and its invoke method
    with patch("luma_core.llm.ChatGoogleGenerativeAI") as mock_chat_class:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = AIMessage(content="Test Response")
        mock_chat_class.return_value = mock_instance
        
        tracked_api._generate([])
    
    # Check that it used an API key and the provider is gemini-api
    found_api = False
    for call in mock_record.call_args_list:
        if call.kwargs.get("provider") == "gemini-api":
            account = call.kwargs.get("account")
            # Should be masked API key
            assert account.startswith("****")
            found_api = True
    assert found_api

    # 2. Test Gemini CLI (should only use Profiles)
    cli_model = GeminiCLIModel(model="gemini-2.5-flash")
    tracked_cli = TrackedModel(model=cli_model)
    
    with patch("luma_core.llm.subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Success", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        tracked_cli._generate([])
    
    # Check that it used a profile (not masked) and the provider is gemini-cli
    found_cli = False
    for call in mock_record.call_args_list:
        if call.kwargs.get("provider") == "gemini-cli":
            account = call.kwargs.get("account")
            assert account in ["personal", "work"]
            found_cli = True
    assert found_cli
