import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from luma_core.tools import update_multi_repo_docs

class TestToolsCodeDiff(unittest.TestCase):
    @patch('luma_core.tools.ui.safe_input')
    @patch('luma_core.tools.subprocess.run')
    @patch('luma_core.tools.gather_git_data_for_docs')
    @patch('luma_core.tools.ai_generate_changelog_entry')
    @patch('os.remove')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="# Changelog\n\n## [Unreleased]\n")
    def test_update_multi_repo_docs_graceful_missing_code_cli(
        self, mock_open_file, mock_exists, mock_remove, mock_ai_changelog, 
        mock_gather_git, mock_subprocess_run, mock_safe_input
    ):
        # Setup
        repo_configs = [
            {"name": "TestRepo", "path": "/mock/repo", "repo": "test/test"}
        ]
        
        # Mock file existence for CHANGELOG
        def mock_exists_side_effect(path):
            if path.endswith("CHANGELOG.md"):
                return True
            if path.endswith("README.md"):
                return False
            return True
            
        mock_exists.side_effect = mock_exists_side_effect
        
        # Mock git data and ai output
        mock_gather_git.return_value = {"commit_log": ["feat: test"], "changed_files": ["test.py"]}
        mock_ai_changelog.return_value = "## [Unreleased]\n- feat: test"
        
        # Mock user selecting to update CHANGELOG and save it
        mock_safe_input.side_effect = ["1", "y"]
        
        # Make subprocess.run raise FileNotFoundError to simulate missing code CLI
        mock_subprocess_run.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'code'")
        
        # Execution
        results = update_multi_repo_docs(repo_configs)
        
        # Assertions
        # The execution should not crash and should return a successful result
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]["error"])
        self.assertIn("CHANGELOG.md", results[0]["files_updated"])
        
if __name__ == '__main__':
    unittest.main()
