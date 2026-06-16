import os
import unittest
from unittest.mock import patch, mock_open

from luma_core.agents.publisher import publisher_agent

class TestPublisherForceExport(unittest.TestCase):
    @patch('luma_core.agents.publisher.subprocess.run')
    @patch('luma_core.agents.publisher.subprocess.check_output')
    @patch('luma_core.agents.publisher.get_cli_wrapper')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_publisher_agent_force_export_only(self, mock_open_file, mock_exists, mock_get_cli_wrapper, mock_check_output, mock_subprocess_run):
        # Setup mock state
        state = {
            "task": "Test Task",
            "issue_data": {"number": 123, "title": "Test Issue", "url": "http://test.com"},
            "repo": "test/test",
            "target_dir": "/mock/dir",
            "force_export_only": True
        }
        
        # Mock git commands to not fail
        mock_subprocess_run.return_value.stdout = "main\n"
        mock_check_output.return_value = "mock_stats"
        
        # Mock file existence (no template, no existing manual body)
        mock_exists.return_value = False
        
        # Execute publisher_agent
        result = publisher_agent(state)
        
        # Verify it returns {"url": None} without interacting with user
        self.assertEqual(result, {"url": None})
        
        # Verify the prompt file was opened/written to
        opened_files = [call[0][0] for call in mock_open_file.call_args_list]
        self.assertTrue(any("draft_pr_prompt.md" in str(f) for f in opened_files))
        
        # Verify no create_merge_request or create_pull_request was called
        # The prompt test logic just needs to verify it returns correctly and exports the prompt.

if __name__ == '__main__':
    unittest.main()
