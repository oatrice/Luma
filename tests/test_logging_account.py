import pytest
from unittest.mock import MagicMock, patch
from luma_core.llm import FallbackModel, GeminiCLIModel, _mask_account

def test_mask_account_api_key():
    assert _mask_account("AIzaTestKey12345678") == "****5678"
    assert _mask_account("sk-TestKeyOpenAI1234") == "****1234"
    assert _mask_account("very-long-custom-api-key-string-more-than-24") == "****n-24"

def test_mask_account_profile():
    assert _mask_account("personal") == "personal"
    assert _mask_account("work") == "work"
    assert _mask_account(None) is None

@patch("luma_core.usage_tracker.record_llm_event")
def test_fallback_model_logs_masked_account(mock_record):
    # Use real model instance but mock its _generate
    mock_model = GeminiCLIModel(model="gemini-2.5-pro")
    mock_model._generate = MagicMock(return_value=MagicMock())
    mock_model.last_account_used = "AIza_Test_Key_9999"
    
    # Create FallbackModel
    fallback = FallbackModel(models=[mock_model])
    
    # Trigger generation
    with patch("luma_core.llm._resolve_model_info", return_value=("gemini_cli", "gemini-2.5-pro", "gemini-cli:gemini-2.5-pro", "general")):
        fallback._generate([])
    
    # Verify record_llm_event was called with masked account
    assert mock_record.called
    # Check all calls to see if any have the masked account
    found = False
    for call in mock_record.call_args_list:
        if call.kwargs.get("account") == "****9999":
            found = True
            break
    assert found, f"Masked account not found in calls: {mock_record.call_args_list}"

@patch("luma_core.usage_tracker.record_llm_event")
def test_fallback_model_logs_profile_name(mock_record):
    # Use real model instance
    mock_model = GeminiCLIModel(model="gemini-2.5-pro")
    mock_model._generate = MagicMock(return_value=MagicMock())
    mock_model.last_account_used = "work_profile"
    
    # Create FallbackModel
    fallback = FallbackModel(models=[mock_model])
    
    # Trigger generation
    with patch("luma_core.llm._resolve_model_info", return_value=("gemini_cli", "gemini-2.5-pro", "gemini-cli:gemini-2.5-pro", "general")):
        fallback._generate([])
    
    # Verify record_llm_event was called with full profile name
    assert mock_record.called
    found = False
    for call in mock_record.call_args_list:
        if call.kwargs.get("account") == "work_profile":
            found = True
            break
    assert found
