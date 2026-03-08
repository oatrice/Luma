import pytest
from unittest.mock import patch, MagicMock
from luma_core.tools import suggest_version_from_git

@patch("subprocess.run")
@patch("luma_core.tools.get_llm")
def test_suggest_version_ios_detection(mock_get_llm, mock_run):
    # Setup: Mock git logs containing iOS changes
    mock_log = MagicMock()
    mock_log.returncode = 0
    mock_log.stdout = "feat: added new swift view\nfix: resolved ios crash"
    
    mock_diff = MagicMock()
    mock_diff.returncode = 0
    mock_diff.stdout = " Platforms/iOS/Project.xcodeproj/project.pbxproj | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)"
    
    # Mock current version from CHANGELOG or file
    # We need to mock the grep/cat command in suggest_version_from_git
    def mock_run_side_effect(cmd, **kwargs):
        if "grep" in cmd:
            res = MagicMock()
            res.returncode = 0
            res.stdout = "1.0.0"
            return res
        return mock_log if "log" in cmd else mock_diff

    mock_run.side_effect = mock_run_side_effect

    # Mock AI response
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "MINOR"
    mock_get_llm.return_value = mock_llm

    # Run
    # Note: suggest_version_from_git currently has hardcoded paths for Android.
    # We expect it to return "1.1.0" once we add iOS support.
    version = suggest_version_from_git("/mock/project")
    
    assert version == "1.1.0"
