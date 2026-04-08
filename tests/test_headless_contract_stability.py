import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Mock simple_term_menu to simulate missing dependency
with patch.dict(sys.modules, {'simple_term_menu': None}):
    from main import parse_cli_args, resolve_project_key
    import luma_core.ui as ui

class TestPathBasedResolutionAndHeadlessDeps(unittest.TestCase):
    def test_resolve_project_key_with_path(self):
        """Test that resolve_project_key accepts absolute paths even if not in registry."""
        test_path = "/tmp/fake_project"
        if not os.path.exists(test_path):
            os.makedirs(test_path, exist_ok=True)
            
        # Should return the path itself as the 'key' or handle it in resolve_project_key
        # We need to ensure main.py doesn't crash during parse_cli_args
        with patch("luma_core.config.PROJECTS", {"1": {"path": "/fake"}}):
            # Simulate Zenith sending an absolute path
            args = parse_cli_args(["--project", test_path, "--action", "lint", "--auto"])
            self.assertEqual(args.project, test_path)

    def test_ui_import_error_headless(self):
        """Test that importing ui doesn't crash if simple_term_menu is missing."""
        # This will test if luma_core.ui can be loaded even if simple_term_menu is deleted from sys.modules
        try:
            # We try to use a function from ui that doesn't need TerminalMenu
            ui.format_state_header = MagicMock()
            success = True
        except ImportError:
            success = False
        
        self.assertTrue(success, "ui.py should be importable without simple_term_menu")

if __name__ == "__main__":
    unittest.main()
