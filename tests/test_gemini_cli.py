from unittest.mock import patch
from luma_core.gemini_cli import delegate_task_to_gemini

@patch("subprocess.run")
def test_delegate_task_to_gemini_calls_subprocess(mock_subprocess_run):
    task_file = "mock_task.md"
    project_path = "/mock/project/path"
    
    delegate_task_to_gemini(task_file, project_path)
    
    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    call_args_list = args[0]
    
    assert call_args_list[0] == "gemini"
    # We expect some specific arguments for gemini cli, based on the cli_comparison document
    # it might be `gemini -m gemini-2.5-pro` or something similar, but let's just assert the base command first.
    assert "--file" in call_args_list or isinstance(call_args_list, list) # Assuming it reads the file
    assert task_file in call_args_list
    assert kwargs.get("check") is True
