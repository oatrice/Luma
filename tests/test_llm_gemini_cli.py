import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from luma_core.llm import get_llm, GeminiCLIModel, FallbackModel, TrackedModel

def test_get_llm_returns_gemini_cli_model():
    with patch("luma_core.config.LLM_PROVIDER", "gemini_cli"):
        llm = get_llm()
        if isinstance(llm, FallbackModel):
            assert any(isinstance(m, GeminiCLIModel) for m in llm.models)
        elif isinstance(llm, TrackedModel):
            assert isinstance(llm.model, GeminiCLIModel)
        else:
            assert isinstance(llm, GeminiCLIModel)

@patch("subprocess.run")
@patch("subprocess.Popen")
def test_gemini_cli_model_invoke(mock_subprocess_popen, mock_subprocess_run):
    from unittest.mock import MagicMock
    
    # Mock subprocess.run for --list-sessions
    mock_run_result = MagicMock()
    mock_run_result.returncode = 0
    mock_run_result.stdout = "Available sessions for this project (0):"
    mock_subprocess_run.return_value = mock_run_result

    # Mock subprocess return value
    mock_process = MagicMock()
    # Mock communicate to return stdout and stderr
    mock_process.communicate.return_value = ("This is a mock response from gemini cli", "")
    mock_process.returncode = 0
    mock_subprocess_popen.return_value = mock_process
    
    model = GeminiCLIModel(model="gemini-2.5-pro", temperature=0.7)
    messages = [HumanMessage(content="Hello Gemini CLI")]
    
    response = model.invoke(messages)
    
    # Check that subprocess.Popen was called at least once
    assert mock_subprocess_popen.called
    
    # Find the specific call to the "gemini" CLI
    gemini_call = None
    for call in mock_subprocess_popen.call_args_list:
        args_list = call[0][0]
        if args_list and args_list[0] == "gemini":
            gemini_call = call
            break
            
    assert gemini_call is not None, "gemini CLI was not called"
    
    # Check how Popen was called
    call_args, call_kwargs = gemini_call
    
    args_list = call_args[0]
    assert args_list[0] == "gemini"
    assert "-m" in args_list
    assert "gemini-2.5-pro" in args_list
    assert "-p" not in args_list # -p should no longer be used
    
    # Check if prompt was passed to communicate via STDIN
    mock_process.communicate.assert_called_once()
    communicate_kwargs = mock_process.communicate.call_args[1]
    assert "input" in communicate_kwargs
    assert "Hello Gemini CLI" in communicate_kwargs["input"]
    
    # Check response parsing
    assert response.content == "This is a mock response from gemini cli"

@patch("subprocess.Popen")
def test_gemini_cli_uses_model_specific_timeout(mock_subprocess_popen):
    from unittest.mock import MagicMock
    
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("mock response", "")
    mock_process.returncode = 0
    mock_subprocess_popen.return_value = mock_process
    
    # flash-preview should have 90s
    model = GeminiCLIModel(model="gemini-3-flash-preview", temperature=0.7)
    messages = [HumanMessage(content="Hello")]
    
    # Mock _get_luma_version or others if needed since invoke might call usage tracker
    with patch("luma_core.usage_tracker.record_llm_event"):
        model.invoke(messages)
        
    mock_process.communicate.assert_called_once()
    kwargs = mock_process.communicate.call_args[1]
    assert kwargs.get("timeout") == 90

@patch("subprocess.Popen")
@patch("time.sleep")
def test_gemini_cli_skips_retry_on_rate_limit(mock_sleep, mock_subprocess_popen):
    from unittest.mock import MagicMock
    
    mock_process = MagicMock()
    # Mock to return rate limit error on first try
    mock_process.communicate.return_value = ("", "HTTP Error 429: Too Many Requests")
    mock_process.returncode = 1
    mock_subprocess_popen.return_value = mock_process
    
    messages = [HumanMessage(content="Hello")]

    import pytest

    with patch("luma_core.config.GOOGLE_API_KEYS", []):
        with patch("luma_core.config.GEMINI_CLI_PROFILES", []):
            model = GeminiCLIModel(model="gemini-2.5-flash", temperature=0.7)
            with pytest.raises(RuntimeError) as exc_info:
                model.invoke(messages)
        
    assert "HTTP Error 429: Too Many Requests" in str(exc_info.value)
    
    # Should only try twice (Attempt 1, then Attempt 2 which fails immediately due to rate limit)
    # But wait, attempt 1 failed, so it sleeps and then tries attempt 2.
    # Should try all available credentials
    assert mock_process.communicate.call_count >= 1
    # Should sleep between attempts
    assert mock_sleep.call_count >= 1


class FailingModel(BaseChatModel):
    model: str = "gemini-2.5-flash"

    @property
    def _llm_type(self) -> str:
        return "gemini-cli:gemini-2.5-flash"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("Request timed out after 120 seconds.")


def test_tracked_model_logs_error_type_on_failure():
    model = TrackedModel(model=FailingModel())
    messages = [HumanMessage(content="Hello")]

    with patch("luma_core.usage_tracker.record_llm_event") as mock_record:
        with pytest.raises(RuntimeError):
            model.invoke(messages)

    assert mock_record.called
    kwargs = mock_record.call_args.kwargs
    assert kwargs["status"] == "error"
    assert kwargs["error_type"] == "TIMEOUT"

@patch("subprocess.Popen")
def test_gemini_cli_oauth_isolation(mock_subprocess_popen):
    from unittest.mock import MagicMock
    import os

    mock_process = MagicMock()
    mock_process.communicate.return_value = ("Isolated Response", "")
    mock_process.returncode = 0
    mock_subprocess_popen.return_value = mock_process

    with patch("luma_core.config.GEMINI_CLI_PROFILES", ["personal-acct"]):
        with patch("luma_core.config.GOOGLE_API_KEYS", []):  # MUST clear API Keys for OAuth to be picked
            model = GeminiCLIModel(model="gemini-2.5-flash")
            messages = [HumanMessage(content="Hello Isolated")]
            
            # Reset CredentialManager singleton for test consistency
            from luma_core.credential_manager import CredentialManager
            CredentialManager.reset_instance()
            
            model.invoke(messages)

    # Check the call to subprocess.Popen
    assert mock_subprocess_popen.called
    kwargs = mock_subprocess_popen.call_args[1]
    env = kwargs.get("env", {})
    
    # Verify HOME was overridden to use the profile path
    expected_home = os.path.expanduser("~/.config/gemini/personal-acct")
    assert env.get("HOME") == expected_home
    assert "GOOGLE_API_KEY" not in env  # Should be popped for OAuth profiles
