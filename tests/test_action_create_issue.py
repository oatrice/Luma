import unittest
import subprocess
import sys
import os
from unittest.mock import MagicMock, patch
from luma_core.actions.issue_actions import action_create_issue
from luma_core.state_manager import LumaState

# Add the project root to sys.path to ensure luma_core is found
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

class TestActionCreateIssue(unittest.TestCase):
    def test_action_create_issue_interactive(self):
        state = LumaState()
        project = {"name": "TestProj", "repo": "owner/repo", "path": "."}
        
        # Mock inputs: Title, Body
        inputs = iter(["Test Title", "Test Body"])
        
        # Mock subprocess.run for gh CLI
        mock_run = MagicMock()
        mock_run.returncode = 0
        mock_run.stdout = "https://github.com/owner/repo/issues/123"
        
        with patch("luma_core.actions.issue_actions.safe_input", lambda _: next(inputs)):
            with patch("subprocess.run", return_value=mock_run) as mocked_subprocess:
                result = action_create_issue(state, project, headless=False)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["number"], 123)
        self.assertEqual(result["url"], "https://github.com/owner/repo/issues/123")
        
        # Verify body has ## Related added
        args, _ = mocked_subprocess.call_args
        cmd = args[0]
        body_index = cmd.index("--body") + 1
        self.assertIn("Test Body", cmd[body_index])
        self.assertIn("## Related: #", cmd[body_index])

    def test_action_create_issue_headless(self):
        state = LumaState()
        project = {"name": "TestProj", "repo": "owner/repo", "path": "."}
        
        mock_run = MagicMock()
        mock_run.returncode = 0
        mock_run.stdout = "https://github.com/owner/repo/issues/456"
        
        with patch("subprocess.run", return_value=mock_run) as mocked_subprocess:
            result = action_create_issue(state, project, title="Headless Title", body="Headless Body", headless=True)
            
        self.assertTrue(result["success"])
        self.assertEqual(result["number"], 456)
        
        # Verify body has ## Related
        args, _ = mocked_subprocess.call_args
        cmd = args[0]
        body_index = cmd.index("--body") + 1
        self.assertEqual("Headless Title", cmd[cmd.index("--title") + 1])
        self.assertIn("Headless Body", cmd[body_index])
        self.assertIn("## Related: #", cmd[body_index])

    def test_action_create_issue_preserves_existing_related(self):
        state = LumaState()
        project = {"name": "TestProj", "repo": "owner/repo", "path": "."}
        
        mock_run = MagicMock()
        mock_run.returncode = 0
        mock_run.stdout = "https://github.com/owner/repo/issues/789"
        
        existing_body = "Something interesting.\n\n## Related: #10"
        
        with patch("subprocess.run", return_value=mock_run) as mocked_subprocess:
            result = action_create_issue(state, project, title="Title", body=existing_body, headless=True)
            
        args, _ = mocked_subprocess.call_args
        cmd = args[0]
        body_passed = cmd[cmd.index("--body") + 1]
        
        self.assertEqual(body_passed, existing_body)
        self.assertEqual(body_passed.count("## Related"), 1)

    def test_action_create_issue_missing_repo(self):
        state = LumaState()
        project = {"name": "NoRepoProj", "path": "."} # Missing 'repo' key
        
        result = action_create_issue(state, project, title="Title", headless=True)
        
        self.assertFalse(result["success"])
        self.assertIn("No repository configured", result["error"])

if __name__ == "__main__":
    unittest.main()
