"""Unit tests for CLI wrapper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from luma_core.cli_wrapper import CLIWrapper, get_cli_wrapper, run_cli_command


class TestCLIWrapper:
    """Test cases for CLIWrapper class."""

    def test_init_with_default_cli(self):
        """Test initialization with default CLI tool from config."""
        with patch('luma_core.cli_wrapper.config.VCS_CLI', 'gh'):
            wrapper = CLIWrapper()
            assert wrapper.cli_tool == 'gh'

    def test_init_with_explicit_cli(self):
        """Test initialization with explicit CLI tool."""
        wrapper = CLIWrapper('glab')
        assert wrapper.cli_tool == 'glab'

    def test_init_with_invalid_cli(self):
        """Test initialization with invalid CLI tool raises ValueError."""
        with pytest.raises(ValueError, match="Invalid VCS_CLI"):
            CLIWrapper('invalid')

    def test_get_token_env_var_gh(self):
        """Test get_token_env_var returns GITHUB_TOKEN for gh."""
        wrapper = CLIWrapper('gh')
        assert wrapper.get_token_env_var() == 'GITHUB_TOKEN'

    def test_get_token_env_var_glab(self):
        """Test get_token_env_var returns GITLAB_TOKEN for glab."""
        wrapper = CLIWrapper('glab')
        assert wrapper.get_token_env_var() == 'GITLAB_TOKEN'

    @patch('luma_core.cli_wrapper.config.GITHUB_TOKEN', 'test_gh_token')
    @patch('luma_core.cli_wrapper.config.GITLAB_TOKEN', 'test_glab_token')
    @patch('luma_core.cli_wrapper.config.VCS_TOKEN', None)
    def test_get_token_gh(self):
        """Test get_token returns GITHUB_TOKEN for gh."""
        wrapper = CLIWrapper('gh')
        assert wrapper.get_token() == 'test_gh_token'

    @patch('luma_core.cli_wrapper.config.GITHUB_TOKEN', 'test_gh_token')
    @patch('luma_core.cli_wrapper.config.GITLAB_TOKEN', 'test_glab_token')
    @patch('luma_core.cli_wrapper.config.VCS_TOKEN', None)
    def test_get_token_glab(self):
        """Test get_token returns GITLAB_TOKEN for glab."""
        wrapper = CLIWrapper('glab')
        assert wrapper.get_token() == 'test_glab_token'

    @patch('subprocess.run')
    def test_run_cli_command_gh(self, mock_run):
        """Test run_cli_command executes gh command."""
        mock_run.return_value = Mock(stdout='test output')
        wrapper = CLIWrapper('gh')
        result = wrapper.run_cli_command(['issue', 'list'])
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'gh'
        assert args[1:] == ['issue', 'list']
        assert result == 'test output'

    @patch('subprocess.run')
    def test_run_cli_command_glab(self, mock_run):
        """Test run_cli_command executes glab command."""
        mock_run.return_value = Mock(stdout='test output')
        wrapper = CLIWrapper('glab')
        result = wrapper.run_cli_command(['issue', 'list'])
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'glab'
        assert args[1:] == ['issue', 'list']
        assert result == 'test output'

    @patch('subprocess.run')
    def test_run_cli_command_no_capture(self, mock_run):
        """Test run_cli_command with capture_output=False."""
        mock_run.return_value = None
        wrapper = CLIWrapper('gh')
        result = wrapper.run_cli_command(['issue', 'list'], capture_output=False)
        
        mock_run.assert_called_once()
        assert result == ''


class TestGetCLIWrapper:
    """Test cases for get_cli_wrapper function."""

    def test_get_cli_wrapper_default(self):
        """Test get_cli_wrapper returns wrapper with config default."""
        with patch('luma_core.cli_wrapper.config.VCS_CLI', 'gh'):
            wrapper = get_cli_wrapper()
            assert wrapper.cli_tool == 'gh'

    def test_get_cli_wrapper_with_override(self):
        """Test get_cli_wrapper with explicit override."""
        wrapper = get_cli_wrapper('glab')
        assert wrapper.cli_tool == 'glab'

    def test_get_cli_wrapper_caches_default(self):
        """Test get_cli_wrapper caches default wrapper instance."""
        with patch('luma_core.cli_wrapper.config.VCS_CLI', 'gh'):
            wrapper1 = get_cli_wrapper()
            wrapper2 = get_cli_wrapper()
            assert wrapper1 is wrapper2


class TestRunCLICommand:
    """Test cases for run_cli_command convenience function."""

    @patch('luma_core.cli_wrapper.get_cli_wrapper')
    def test_run_cli_command_default(self, mock_get_wrapper):
        """Test run_cli_command uses default wrapper."""
        mock_wrapper = Mock()
        mock_wrapper.run_cli_command.return_value = 'test output'
        mock_get_wrapper.return_value = mock_wrapper
        
        result = run_cli_command(['issue', 'list'])
        
        mock_get_wrapper.assert_called_once_with(None)
        mock_wrapper.run_cli_command.assert_called_once_with(['issue', 'list'], True)
        assert result == 'test output'

    @patch('luma_core.cli_wrapper.get_cli_wrapper')
    def test_run_cli_command_with_cli_tool(self, mock_get_wrapper):
        """Test run_cli_command with explicit CLI tool."""
        mock_wrapper = Mock()
        mock_wrapper.run_cli_command.return_value = 'test output'
        mock_get_wrapper.return_value = mock_wrapper
        
        result = run_cli_command(['issue', 'list'], cli_tool='glab')
        
        mock_get_wrapper.assert_called_once_with('glab')
        mock_wrapper.run_cli_command.assert_called_once_with(['issue', 'list'], True)
        assert result == 'test output'
