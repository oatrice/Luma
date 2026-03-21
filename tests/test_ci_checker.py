import pytest
import subprocess
import json
from unittest.mock import patch, MagicMock
from luma_core.ci_checker import check_pr_ci_status, get_ci_failure_logs

@patch("subprocess.run")
def test_check_pr_ci_status_all_passed(mock_run):
    # Mock successful gh pr checks output
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps([
            {"name": "build", "state": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "lint", "state": "COMPLETED", "conclusion": "SUCCESS"}
        ])
    )

    result = check_pr_ci_status("123", "org/repo")
    
    assert result["all_passed"] is True
    assert len(result["failed_checks"]) == 0
    assert len(result["checks"]) == 2

@patch("subprocess.run")
def test_check_pr_ci_status_some_failed(mock_run):
    # Mock failed gh pr checks output
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps([
            {"name": "build", "state": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "test", "state": "COMPLETED", "conclusion": "FAILURE"}
        ])
    )

    result = check_pr_ci_status("123", "org/repo")
    
    assert result["all_passed"] is False
    assert len(result["failed_checks"]) == 1
    assert result["failed_checks"][0]["name"] == "test"

@patch("subprocess.run")
def test_get_ci_failure_logs(mock_run):
    # Mock gh run view output
    long_log_output = "Error details... " * 500  # Will exceed 3000 chars
    
    # Mocking first run to get run_id, second to get logs
    def side_effect(*args, **kwargs):
        cmd = args[0]
        if "gh run list" in " ".join(cmd):
            # We need to find run_id from checks, which might just use gh pr checks under the hood,
            # or gh run list. Let's assume get_ci_failure_logs uses `gh run list --limit 10 --json` for simplicity.
            return MagicMock(returncode=0, stdout=json.dumps([{"databaseId": 999, "name": "test", "conclusion": "failure"}]))
        elif "gh run view 999" in " ".join(cmd):
            return MagicMock(returncode=0, stdout=long_log_output)
        return MagicMock(returncode=1)

    mock_run.side_effect = side_effect

    logs = get_ci_failure_logs("123", "org/repo", "test")
    
    assert "Error details..." in logs
    assert len(logs) <= 3000
    assert "...[truncated by luma]..." in logs
