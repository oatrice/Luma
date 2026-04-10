"""
Tests for Feature #23: Luma Header Enhancement & UX Improvements
Issues: #74, #72, #71, #60
"""

import pytest
from unittest.mock import patch, MagicMock


class TestMenuOrdering:
    """Test FR4: Menu option 'A' appears in top 3 positions"""

    def test_auto_full_workflow_in_top_3_positions(self):
        """Verify 'A' Auto Full Workflow is in top 3 menu positions"""
        from main import MENU_ACTIONS
        
        # Get ordered keys
        keys = list(MENU_ACTIONS.keys())
        
        # Find position of 'A'
        try:
            position_a = keys.index("A")
        except ValueError:
            pytest.fail("'A' key not found in MENU_ACTIONS")
        
        # Assert 'A' is in top 3 positions (0, 1, or 2)
        assert position_a < 3, f"'A' is at position {position_a}, expected top 3"

    def test_exit_remains_first_position(self):
        """Verify '0' Exit remains at first position"""
        from main import MENU_ACTIONS
        
        keys = list(MENU_ACTIONS.keys())
        assert keys[0] == "0", f"Expected '0' at position 0, got '{keys[0]}'"


class TestVersionFormat:
    """Test FR6: All version references use 0.x.x format"""

    def test_version_file_format(self):
        """VERSION file must use 0.x.x format"""
        with open("VERSION", "r") as f:
            version = f.read().strip()
        
        # Must match 0.x.x format
        import re
        assert re.match(r"^0\.\d+\.\d+", version), f"VERSION '{version}' must use 0.x.x format"

    def test_changelog_version_format(self):
        """CHANGELOG.md versions must use 0.x.x format"""
        import re
        
        with open("CHANGELOG.md", "r") as f:
            content = f.read()
        
        # Find all version headers
        versions = re.findall(r"##\s*\[(\d+\.\d+\.[^\]]+)\]", content)
        
        # All versions should be 0.x.x
        for version in versions:
            assert version.startswith("0."), f"Version '{version}' must use 0.x.x format"


class TestAIBrainSyncFiltering:
    """Test FR5: AI Brain sync filters by project context"""

    def test_antigravity_get_all_sessions_accepts_project_filter(self):
        """AntigravityBrain.get_all_sessions should accept project_dir parameter"""
        from luma_core.ai_brain_sync import AntigravityBrain
        
        # Check method signature accepts project_dir
        import inspect
        sig = inspect.signature(AntigravityBrain.get_all_sessions)
        params = list(sig.parameters.keys())
        
        assert "project_dir" in params, "get_all_sessions must accept project_dir parameter"

    def test_gemini_cli_get_all_sessions_accepts_project_filter(self):
        """GeminiCLIBrain.get_all_sessions should accept project_dir parameter"""
        from luma_core.ai_brain_sync import GeminiCLIBrain
        
        # Check method signature accepts project_dir
        import inspect
        sig = inspect.signature(GeminiCLIBrain.get_all_sessions)
        params = list(sig.parameters.keys())
        
        assert "project_dir" in params, "get_all_sessions must accept project_dir parameter"

    def test_antigravity_sessions_filtered_by_project(self):
        """AntigravityBrain.get_all_sessions should filter sessions by project name"""
        from luma_core.ai_brain_sync import AntigravityBrain
        from unittest.mock import patch, mock_open
        
        # Mock session data with different projects
        mock_sessions = [
            "/home/user/.gemini/antigravity/brain/session-1",
            "/home/user/.gemini/antigravity/brain/session-2",
            "/home/user/.gemini/antigravity/brain/session-3",
        ]
        
        session_contents = {
            "session-1": "Task for Luma project issue #74",
            "session-2": "Task for Cerebro project issue #60", 
            "session-3": "Another Luma task issue #71",
        }
        
        def mock_listdir(path):
            return ["session-1", "session-2", "session-3"]
        
        def mock_isdir(path):
            return True
        
        def mock_exists(path):
            return True
        
        def mock_getmtime(path):
            # Return different times
            return int(path.split("-")[-1])
        
        def mock_open_file(path, *args, **kwargs):
            session_id = path.split("/")[-2]
            return mock_open(read_data=session_contents.get(session_id, ""))()
        
        with patch("os.path.exists", side_effect=mock_exists):
            with patch("os.listdir", side_effect=mock_listdir):
                with patch("os.path.isdir", side_effect=mock_isdir):
                    with patch("os.path.getmtime", side_effect=mock_getmtime):
                        with patch("builtins.open", side_effect=mock_open_file):
                            # Call with Luma project filter
                            sessions = AntigravityBrain.get_all_sessions(project_dir="/Projects/Luma")
                            
                            # Should only return Luma-related sessions
                            for session in sessions:
                                preview = session["preview"].lower()
                                assert "luma" in preview, f"Session {session['session_id']} not related to Luma"

    def test_gemini_sessions_filtered_by_project(self):
        """GeminiCLIBrain.get_all_sessions should filter sessions by project name"""
        from luma_core.ai_brain_sync import GeminiCLIBrain
        from unittest.mock import patch, mock_open
        import json
        
        # Mock session data with different projects
        mock_sessions = [
            "session-luma-74.json",
            "session-cerebro-60.json",
            "session-luma-71.json",
        ]
        
        session_data = {
            "session-luma-74.json": {"messages": [{"content": [{"text": "Task for Luma issue #74"}]}]},
            "session-cerebro-60.json": {"messages": [{"content": [{"text": "Task for Cerebro issue #60"}]}]},
            "session-luma-71.json": {"messages": [{"content": [{"text": "Another Luma task #71"}]}]},
        }
        
        def mock_listdir(path):
            return mock_sessions
        
        def mock_exists(path):
            return True
        
        def mock_getmtime(path):
            return int(path.split("-")[-1].replace(".json", ""))
        
        def mock_open_file(path, *args, **kwargs):
            filename = path.split("/")[-1]
            return mock_open(read_data=json.dumps(session_data.get(filename, {})))()
        
        with patch("os.path.exists", side_effect=mock_exists):
            with patch("os.listdir", side_effect=mock_listdir):
                with patch("os.path.getmtime", side_effect=mock_getmtime):
                    with patch("builtins.open", side_effect=mock_open_file):
                        # Call with Luma project filter
                        sessions = GeminiCLIBrain.get_all_sessions(project_dir="/Projects/Luma")
                        
                        # Should only return Luma-related sessions
                        for session in sessions:
                            preview = session["preview"].lower()
                            assert "luma" in preview, f"Session {session['session_id']} not related to Luma"


class TestHeaderDisplay:
    """Test FR1-FR3: Header display features"""

    def test_header_shows_folder_path(self, capsys):
        """Header displays folder path"""
        from luma_core.ui import display_header
        from luma_core.state_manager import LumaState
        
        state = LumaState()
        project = {
            "name": "TestProject",
            "path": "/Users/dev/Projects/TestProject",
            "kanban_number": 5
        }
        
        display_header(state, project)
        captured = capsys.readouterr()
        
        assert "📁 Folder" in captured.out, "Header should show folder path"
        assert "TestProject" in captured.out, "Header should contain project name"

    def test_header_shows_github_project(self, capsys):
        """Header displays GitHub Project number when kanban_number configured"""
        from luma_core.ui import display_header
        from luma_core.state_manager import LumaState
        
        state = LumaState()
        project = {
            "name": "TestProject",
            "path": "/Users/dev/Projects/TestProject",
            "kanban_number": 5
        }
        
        display_header(state, project)
        captured = capsys.readouterr()
        
        assert "🐙 GH Proj" in captured.out, "Header should show GitHub Project"
        assert "Project #5" in captured.out, "Header should show project number"

    def test_long_path_truncation(self, capsys):
        """Long folder paths (>40 chars) are truncated"""
        from luma_core.ui import display_header
        from luma_core.state_manager import LumaState
        
        state = LumaState()
        long_path = "/very/long/path/to/the/project/directory/name"
        project = {
            "name": "TestProject",
            "path": long_path,
            "kanban_number": None
        }
        
        display_header(state, project)
        captured = capsys.readouterr()
        
        # Should show truncated path with ellipsis
        assert "..." in captured.out, "Long path should be truncated with ellipsis"


class TestWorktreeDetection:
    """Test worktree detection utilities"""

    def test_get_main_repo_name_from_worktree_returns_none_for_regular_repo(self):
        """get_main_repo_name_from_worktree returns None for regular repo"""
        from luma_core.tools import get_main_repo_name_from_worktree
        
        with patch("luma_core.tools.is_git_worktree", return_value=False):
            result = get_main_repo_name_from_worktree("/some/path")
            assert result is None, "Should return None for regular repo"

    def test_get_main_repo_name_from_worktree_returns_name_for_worktree(self):
        """get_main_repo_name_from_worktree returns main repo name for worktree"""
        from luma_core.tools import get_main_repo_name_from_worktree
        
        mock_worktree_output = "worktree /Users/dev/Projects/Luma\nHEAD abc123\nbranch main\n\nworktree /Users/dev/Projects/Luma-worktrees/feature\nHEAD def456\nbranch feature"
        
        with patch("luma_core.tools.is_git_worktree", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout=mock_worktree_output, returncode=0)
                result = get_main_repo_name_from_worktree("/Users/dev/Projects/Luma-worktrees/feature")
                assert result == "Luma", f"Expected 'Luma', got '{result}'"
