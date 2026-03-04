import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage
from luma_core.llm import get_llm, GeminiCLIModel

def test_get_llm_returns_gemini_cli_model():
    with patch("luma_core.config.LLM_PROVIDER", "gemini_cli"):
        llm = get_llm()
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
