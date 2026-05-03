"""Tests for platform_detector.py - VCS CLI priority functionality."""

import pytest
from unittest.mock import patch, MagicMock
import os

from luma_core.platform_detector import (
    check_pr_status_unified,
    get_open_pr_unified,
    update_pull_request_unified,
    create_pull_request_unified
)


class TestVCSCLIPriority:
    """Test VCS_CLI configuration priority over URL regex matching."""

    @pytest.fixture
    def mock_glab_wrapper(self):
        """Mock glab CLI wrapper."""
        with patch('luma_core.cli_wrapper.get_cli_wrapper') as mock_get_wrapper:
            mock_wrapper = MagicMock()
            mock_get_wrapper.return_value = mock_wrapper
            mock_wrapper.run_cli_command.return_value = "State: opened"
            yield mock_wrapper

    @pytest.fixture
    def mock_gh_wrapper(self):
        """Mock gh CLI wrapper."""
        with patch('luma_core.cli_wrapper.get_cli_wrapper') as mock_get_wrapper:
            mock_wrapper = MagicMock()
            mock_get_wrapper.return_value = mock_wrapper
            mock_wrapper.run_cli_command.return_value = '{"state": "open"}'
            yield mock_wrapper

    @pytest.fixture
    def setup_vcs_cli_env(self):
        """Setup VCS_CLI environment variable."""
        original_vcs_cli = os.environ.get('VCS_CLI')
        yield
        if original_vcs_cli:
            os.environ['VCS_CLI'] = original_vcs_cli
        elif 'VCS_CLI' in os.environ:
            del os.environ['VCS_CLI']

    class TestCheckPRStatusUnified:
        """Test check_pr_status_unified with VCS_CLI priority."""

        @patch('luma_core.config.VCS_CLI', 'glab')
        def test_vcs_cli_glab_with_gitlab_url(self, mock_glab_wrapper):
            """Test VCS_CLI=glab with GitLab URL uses glab."""
            result = check_pr_status_unified('https://gitlab.com/oatricedev/Luma/-/merge_requests/93')
            
            assert result['merged'] is False
            assert result['state'] == 'opened'
            assert result['error'] is None
            mock_glab_wrapper.run_cli_command.assert_called_once()

        @patch('luma_core.config.VCS_CLI', 'glab')
        def test_vcs_cli_glab_with_github_url_should_error(self):
            """Test VCS_CLI=glab with GitHub URL should return error."""
            result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65')
            
            assert result['merged'] is False
            assert result['state'] == 'unknown'
            assert 'VCS_CLI=glab but GitHub URL provided' in result['error']

        @patch('luma_core.config.VCS_CLI', 'glab')
        def test_vcs_cli_glab_with_github_url_self_healing(self, mock_gh_wrapper):
            """Test VCS_CLI=glab with GitHub URL self-healing fallback."""
            mock_gh_wrapper.run_cli_command.return_value = '{"state": "closed"}'
            
            result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65', allow_self_healing=True)
            
            assert result['merged'] is False
            assert result['state'] == 'closed'
            assert result['error'] is None

        @patch('luma_core.config.VCS_CLI', 'gh')
        def test_vcs_cli_gh_with_github_url(self, mock_gh_wrapper):
            """Test VCS_CLI=gh with GitHub URL uses gh."""
            result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65')
            
            assert result['merged'] is False
            assert result['state'] == 'open'
            assert result['error'] is None
            mock_gh_wrapper.run_cli_command.assert_called_once()

        @patch('luma_core.config.VCS_CLI', 'gh')
        def test_vcs_cli_gh_with_gitlab_url_should_error(self):
            """Test VCS_CLI=gh with GitLab URL should return error."""
            result = check_pr_status_unified('https://gitlab.com/oatricedev/Luma/-/merge_requests/93')
            
            assert result['merged'] is False
            assert result['state'] == 'unknown'
            assert 'VCS_CLI=gh but GitLab URL provided' in result['error']

        def test_vcs_cli_unset_with_github_url_fallback(self, mock_gh_wrapper, setup_vcs_cli_env):
            """Test VCS_CLI unset with GitHub URL falls back to URL regex."""
            # Remove VCS_CLI from environment to simulate unset
            if 'VCS_CLI' in os.environ:
                del os.environ['VCS_CLI']
            
            # Need to reload the module to pick up the change
            import importlib
            import luma_core.platform_detector
            importlib.reload(luma_core.platform_detector)
            
            result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65')
            
            assert result['merged'] is False
            assert result['state'] == 'open'
            assert result['error'] is None

        def test_vcs_cli_unset_with_gitlab_url_fallback(self, mock_glab_wrapper, setup_vcs_cli_env):
            """Test VCS_CLI unset with GitLab URL falls back to URL regex."""
            # Remove VCS_CLI from environment to simulate unset
            if 'VCS_CLI' in os.environ:
                del os.environ['VCS_CLI']
            
            # Need to reload the module to pick up the change
            import importlib
            import luma_core.platform_detector
            importlib.reload(luma_core.platform_detector)
            
            result = check_pr_status_unified('https://gitlab.com/oatricedev/Luma/-/merge_requests/93')
            
            assert result['merged'] is False
            assert result['state'] == 'opened'
            assert result['error'] is None

    class TestGetOpenPRUnified:
        """Test get_open_pr_unified with VCS_CLI priority."""

        @patch('luma_core.config.VCS_CLI', 'glab')
        @patch('luma_core.platform_detector.detect_repo_platform')
        @patch('luma_core.gitlab_client.get_open_merge_request')
        def test_vcs_cli_glab_with_gitlab_repo(self, mock_get_merge_request, mock_detect_platform, mock_glab_wrapper):
            """Test VCS_CLI=glab with GitLab repo uses glab."""
            mock_detect_platform.return_value = 'gitlab'
            mock_get_merge_request.return_value = {'url': 'https://gitlab.com/oatricedev/Luma/-/merge_requests/93'}
            
            result = get_open_pr_unified('oatricedev/Luma', 'feature-branch')
            
            assert result is not None
            assert 'url' in result
            mock_get_merge_request.assert_called_once_with('oatricedev/Luma', 'feature-branch')

        @patch('luma_core.config.VCS_CLI', 'glab')
        @patch('luma_core.platform_detector.detect_repo_platform')
        def test_vcs_cli_glab_with_github_repo_should_error(self, mock_detect_platform):
            """Test VCS_CLI=glab with GitHub repo should return error."""
            mock_detect_platform.return_value = 'github'
            result = get_open_pr_unified('oatrice/Cerebro', 'feature-branch')
            
            assert result is None

        @patch('luma_core.config.VCS_CLI', 'gh')
        @patch('luma_core.platform_detector.detect_repo_platform')
        @patch('luma_core.github_client.get_open_pr')
        def test_vcs_cli_gh_with_github_repo(self, mock_get_open_pr, mock_detect_platform, mock_gh_wrapper):
            """Test VCS_CLI=gh with GitHub repo uses gh."""
            mock_detect_platform.return_value = 'github'
            mock_get_open_pr.return_value = {'url': 'https://github.com/oatrice/Cerebro/pull/65'}
            
            result = get_open_pr_unified('oatrice/Cerebro', 'feature-branch')
            
            assert result is not None
            assert 'url' in result
            mock_get_open_pr.assert_called_once_with('oatrice/Cerebro', 'feature-branch')

        @patch('luma_core.config.VCS_CLI', 'gh')
        @patch('luma_core.platform_detector.detect_repo_platform')
        def test_vcs_cli_gh_with_gitlab_repo_should_error(self, mock_detect_platform):
            """Test VCS_CLI=gh with GitLab repo should return error."""
            mock_detect_platform.return_value = 'gitlab'
            result = get_open_pr_unified('oatricedev/Luma', 'feature-branch')
            
            assert result is None

    class TestUpdatePullRequestUnified:
        """Test update_pull_request_unified with VCS_CLI priority."""

        @patch('luma_core.config.VCS_CLI', 'glab')
        @patch('luma_core.platform_detector.detect_repo_platform')
        @patch('luma_core.gitlab_client.update_merge_request')
        def test_vcs_cli_glab_with_gitlab_repo(self, mock_update_merge_request, mock_detect_platform, mock_glab_wrapper):
            """Test VCS_CLI=glab with GitLab repo uses glab."""
            mock_detect_platform.return_value = 'gitlab'
            mock_update_merge_request.return_value = "https://gitlab.com/oatricedev/Luma/-/merge_requests/93"
            
            result = update_pull_request_unified('oatricedev/Luma', 93, 'New Title', 'New Body')
            
            assert result is not None
            mock_update_merge_request.assert_called_once_with('oatricedev/Luma', 93, 'New Title', 'New Body')

        @patch('luma_core.config.VCS_CLI', 'glab')
        @patch('luma_core.platform_detector.detect_repo_platform')
        def test_vcs_cli_glab_with_github_repo_should_error(self, mock_detect_platform):
            """Test VCS_CLI=glab with GitHub repo should return error."""
            mock_detect_platform.return_value = 'github'
            result = update_pull_request_unified('oatrice/Cerebro', 65, 'New Title', 'New Body')
            
            assert result is None

        @patch('luma_core.config.VCS_CLI', 'gh')
        @patch('luma_core.platform_detector.detect_repo_platform')
        @patch('luma_core.github_client.update_pull_request')
        def test_vcs_cli_gh_with_github_repo(self, mock_update_pull_request, mock_detect_platform, mock_gh_wrapper):
            """Test VCS_CLI=gh with GitHub repo uses gh."""
            mock_detect_platform.return_value = 'github'
            mock_update_pull_request.return_value = '{"url": "https://github.com/oatrice/Cerebro/pull/65"}'
            
            result = update_pull_request_unified('oatrice/Cerebro', 65, 'New Title', 'New Body')
            
            assert result is not None
            mock_update_pull_request.assert_called_once_with('oatrice/Cerebro', 65, 'New Title', 'New Body')

        @patch('luma_core.config.VCS_CLI', 'gh')
        @patch('luma_core.platform_detector.detect_repo_platform')
        def test_vcs_cli_gh_with_gitlab_repo_should_error(self, mock_detect_platform):
            """Test VCS_CLI=gh with GitLab repo should return error."""
            mock_detect_platform.return_value = 'gitlab'
            result = update_pull_request_unified('oatricedev/Luma', 93, 'New Title', 'New Body')
            
            assert result is None

    class TestCreatePullRequestUnified:
        """Test create_pull_request_unified with VCS_CLI priority."""

        @patch('luma_core.config.VCS_CLI', 'glab')
        @patch('luma_core.platform_detector.detect_repo_platform')
        @patch('luma_core.gitlab_client.create_merge_request')
        def test_vcs_cli_glab_with_gitlab_repo(self, mock_create_merge_request, mock_detect_platform, mock_glab_wrapper):
            """Test VCS_CLI=glab with GitLab repo uses glab."""
            mock_detect_platform.return_value = 'gitlab'
            mock_create_merge_request.return_value = "https://gitlab.com/oatricedev/Luma/-/merge_requests/93"
            
            result = create_pull_request_unified('oatricedev/Luma', 'Title', 'Body', 'feature-branch', 'main')
            
            assert result is not None
            mock_create_merge_request.assert_called_once_with('oatricedev/Luma', 'Title', 'Body', 'feature-branch', 'main')

        @patch('luma_core.config.VCS_CLI', 'glab')
        @patch('luma_core.platform_detector.detect_repo_platform')
        def test_vcs_cli_glab_with_github_repo_should_error(self, mock_detect_platform):
            """Test VCS_CLI=glab with GitHub repo should return error."""
            mock_detect_platform.return_value = 'github'
            result = create_pull_request_unified('oatrice/Cerebro', 'Title', 'Body', 'feature-branch', 'main')
            
            assert result is None

        @patch('luma_core.config.VCS_CLI', 'gh')
        @patch('luma_core.platform_detector.detect_repo_platform')
        @patch('luma_core.github_client.create_pull_request')
        def test_vcs_cli_gh_with_github_repo(self, mock_create_pull_request, mock_detect_platform, mock_gh_wrapper):
            """Test VCS_CLI=gh with GitHub repo uses gh."""
            mock_detect_platform.return_value = 'github'
            mock_create_pull_request.return_value = '{"url": "https://github.com/oatrice/Cerebro/pull/65"}'
            
            result = create_pull_request_unified('oatrice/Cerebro', 'Title', 'Body', 'feature-branch', 'main')
            
            assert result is not None
            mock_create_pull_request.assert_called_once_with('oatrice/Cerebro', 'Title', 'Body', 'feature-branch', 'main')

        @patch('luma_core.config.VCS_CLI', 'gh')
        @patch('luma_core.platform_detector.detect_repo_platform')
        def test_vcs_cli_gh_with_gitlab_repo_should_error(self, mock_detect_platform):
            """Test VCS_CLI=gh with GitLab repo should return error."""
            mock_detect_platform.return_value = 'gitlab'
            result = create_pull_request_unified('oatricedev/Luma', 'Title', 'Body', 'feature-branch', 'main')
            
            assert result is None


if __name__ == '__main__':
    pytest.main([__file__])
