import pytest
from unittest.mock import patch
from luma_core.opencode import delegate_task_to_opencode

@patch("subprocess.run")
def test_delegate_task_to_opencode_calls_subprocess(mock_subprocess_run):
    task_file = "mock_task.md"
    project_path = "/mock/project/path"
    
    delegate_task_to_opencode(task_file, project_path)
    
    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    call_args_list = args[0]
    
    assert call_args_list[0] == "opencode"
    assert call_args_list[1] == "run"
    assert "--file" in call_args_list
    assert task_file in call_args_list
    assert "--dir" in call_args_list
    assert project_path in call_args_list
    assert kwargs.get("check") is True
