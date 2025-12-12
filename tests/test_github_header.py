
import os
import unittest
from unittest.mock import patch
from github_fetcher import get_github_headers

class TestGitHubHeaders(unittest.TestCase):
    @patch("os.getenv")
    def test_authorization_header_uses_bearer(self, mock_getenv):
        # Setup mock token
        mock_getenv.return_value = "ghp_mock_token"
        
        headers = get_github_headers()
        
        # Verify the Authorization header uses 'Bearer' prefix (Best practice for Token V2 & Classic)
        auth_header = headers.get("Authorization", "")
        self.assertTrue(auth_header.startswith("Bearer "), 
                        f"Expected 'Bearer' prefix, but got: '{auth_header}'")

    @patch("os.getenv")
    @patch("requests.patch")
    def test_close_issue_uses_bearer(self, mock_patch, mock_getenv):
        # Setup mock token
        mock_getenv.return_value = "ghp_mock_token"
        
        # Helper to capture headers
        captured_headers = {}
        def side_effect(*args, **kwargs):
            nonlocal captured_headers
            captured_headers = kwargs.get('headers', {})
            mock_resp = unittest.mock.Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"state": "closed"}
            return mock_resp
            
        mock_patch.side_effect = side_effect

        # Import dynamically or via sys.path
        import sys
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from scripts.close_issue import close_issue
        
        # Run function
        # Redirect stdout to suppress print
        from io import StringIO
        with patch('sys.stdout', new=StringIO()):
            close_issue("owner/repo", 1)
        
        # Verify
        auth_header = captured_headers.get("Authorization", "")
        self.assertTrue(auth_header.startswith("Bearer "), 
                        f"Expected 'Bearer' prefix in close_issue, but got: '{auth_header}'")


if __name__ == "__main__":
    unittest.main()
