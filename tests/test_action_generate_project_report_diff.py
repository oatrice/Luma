import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import subprocess
from datetime import date
from luma_core.actions.metrics_actions import action_generate_project_report

class TestActionGenerateProjectReport(unittest.TestCase):
    @patch("luma_core.actions.metrics_actions.input")
    @patch("luma_core.report_generator.generate_report")
    @patch("luma_core.issue_metrics.prefill_metrics_from_roadmap")
    @patch("luma_core.issue_metrics.sync_github_metrics_for_project")
    @patch("os.makedirs")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("subprocess.run")
    def test_action_generate_project_report_calls_code_diff(
        self, mock_run, mock_file_open, mock_exists, mock_makedirs, 
        mock_sync_gh, mock_prefill, mock_gen_report, mock_input
    ):
        # Setup mocks for sync/prefill
        mock_prefill.return_value = {"created": 0, "updated": 0}
        mock_sync_gh.return_value = {"updated": 0, "errors": 0, "paradoxes_fixed": 0}
        # Setup
        project = {
            "name": "Test Project",
            "path": "/mock/project",
            "repo": "oatrice/test-repo"
        }
        state = MagicMock()
        
        # Mock inputs: [Period (Weekly), Date (Today)]
        mock_input.side_effect = ["1", ""]
        
        # Mock report generator
        mock_gen_report.return_value = "New Report Content"
        
        # Mock directory structure and file existence
        # 1. os.path.exists(output_path) -> True (while loop starts)
        # 2. os.path.exists(output_path(1)) -> True (while loop continues)
        # 3. os.path.exists(output_path(2)) -> False (while loop ends)
        # 4. os.path.exists(original_path) -> True (if check for diff)
        mock_exists.side_effect = [True, True, False, True]
        
        # Mock date to be fixed
        with patch("datetime.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 27)
            mock_date.fromisoformat.side_effect = lambda x: date.fromisoformat(x)
            
            # Execute
            action_generate_project_report(state, project)
            
        # Verify code --diff was called
        # Year 2026, Week 13
        expected_base = "/mock/project/docs/reports/weekly_2026-W13"
        expected_original = f"{expected_base}.md"
        expected_output = f"{expected_base}(2).md"
        
        mock_run.assert_called_once_with(["code", "--diff", expected_original, expected_output], check=True)
        
        # Also verify no _diff.md file was created via open()
        # The file open calls should be:
        # 1. Opening original_path to read lines (old implementation used this)
        # 2. Opening output_path to write report content
        # We want to ensure NO file ending in _diff.md is opened for writing.
        for call in mock_file_open.call_args_list:
            args, _ = call
            self.assertFalse(str(args[0]).endswith("_diff.md"))

if __name__ == "__main__":
    unittest.main()
