import pytest
from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from luma_core.llm import CodexCLIModel, FallbackModel, GeminiCLIModel, get_llm


def test_get_llm_returns_codex_cli_with_gemini_cli_fallback():
    with patch("luma_core.config.LLM_PROVIDER", "codex-cli"):
        llm = get_llm()

    assert isinstance(llm, FallbackModel)
    assert isinstance(llm.models[0], CodexCLIModel)
    assert any(isinstance(model, GeminiCLIModel) for model in llm.models[1:])


@patch("subprocess.Popen")
def test_codex_cli_model_invoke_uses_exec_stdin(mock_subprocess_popen):
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("This is a mock response from codex cli", "")
    mock_process.returncode = 0
    mock_subprocess_popen.return_value = mock_process

    model = CodexCLIModel()
    messages = [HumanMessage(content="Hello Codex CLI")]

    response = model.invoke(messages)

    assert mock_subprocess_popen.called
    cmd = mock_subprocess_popen.call_args[0][0]
    assert cmd[0] == "codex"
    assert cmd[1] == "exec"
    assert "-" in cmd

    communicate_kwargs = mock_process.communicate.call_args.kwargs
    assert "Hello Codex CLI" in communicate_kwargs["input"]
    assert response.content == "This is a mock response from codex cli"


@patch("subprocess.Popen", side_effect=FileNotFoundError("codex"))
def test_codex_cli_missing_binary_raises_helpful_error(_mock_subprocess_popen):
    model = CodexCLIModel()

    with pytest.raises(RuntimeError) as exc_info:
        model.invoke([HumanMessage(content="Hello")])

    assert "codex-cli is not installed" in str(exc_info.value)


@patch("subprocess.Popen")
def test_codex_cli_auth_failure_raises_login_hint(mock_subprocess_popen):
    mock_process = MagicMock()
    mock_process.communicate.return_value = ("", "Authentication required. Please login.")
    mock_process.returncode = 1
    mock_subprocess_popen.return_value = mock_process

    model = CodexCLIModel()

    with pytest.raises(RuntimeError) as exc_info:
        model.invoke([HumanMessage(content="Hello")])

    assert "codex login" in str(exc_info.value)
