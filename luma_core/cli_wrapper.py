"""CLI Wrapper for VCS operations.

This module provides a wrapper for executing VCS CLI commands (gh or glab)
based on the VCS_CLI configuration. It abstracts the differences between
GitHub CLI (gh) and GitLab CLI (glab) commands.
"""

import subprocess
import os
import logging
from datetime import datetime
from typing import List, Optional
from luma_core import config


# Setup logging
def _setup_logger():
    """Setup logger for CLI wrapper operations."""
    logger = logging.getLogger('cli_wrapper')
    if logger.handlers:
        return logger
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', '.luma_logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Setup file handler
    log_file = os.path.join(log_dir, f'cli_wrapper_{datetime.now().strftime("%Y-%m-%d")}.log')
    handler = logging.FileHandler(log_file, encoding='utf-8')
    
    # Setup formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger

_logger = _setup_logger()


class CLIWrapper:
    """Wrapper for executing VCS CLI commands with configurable tool."""

    def __init__(self, cli_tool: Optional[str] = None):
        """Initialize CLI wrapper with specified CLI tool.
        
        Args:
            cli_tool: The CLI tool to use ("gh" or "glab"). If None, uses
                     config.VCS_CLI (defaults to "gh").
        """
        self.cli_tool = cli_tool or config.VCS_CLI
        
        # Log initialization
        _logger.info(f"CLI Wrapper initialized with tool: {self.cli_tool}")
        
        # Validate CLI tool
        if self.cli_tool not in ("gh", "glab"):
            raise ValueError(
                f"Invalid VCS_CLI: {self.cli_tool}. Must be 'gh' or 'glab'."
            )

    def run_cli_command(self, args: List[str], capture_output: bool = True) -> str:
        """Execute command using configured CLI tool.
        
        Args:
            args: List of command arguments (excluding the CLI tool itself).
            capture_output: Whether to capture stdout/stderr. If False, 
                          output goes to terminal.
        
        Returns:
            Command output as string if capture_output=True, empty string otherwise.
        
        Raises:
            subprocess.CalledProcessError: If command fails.
        """
        # Convert GitHub CLI commands to GitLab CLI equivalents if needed
        if self.cli_tool == "glab":
            args = self._convert_glab_command(args)
        
        full_command = [self.cli_tool] + args
        
        # Log command execution
        _logger.info(f"Executing CLI command: {' '.join(full_command)}")
        
        # Prepare clean environment
        env = os.environ.copy()
        # Explicitly remove tokens to force usage of system config/keyring
        # if they are not explicitly provided by the Luma config.
        for token_key in ['GITHUB_TOKEN', 'GH_TOKEN', 'GITLAB_TOKEN', 'GL_TOKEN']:
            if token_key in env:
                del env[token_key]
                
        # If Luma config has a specific token for this tool, inject it.
        # But we must NOT inject an expired/invalid token into the CLI environment
        # if we are doing auth commands, so we can read the CLI's internal auth state!
        is_auth_command = len(args) > 0 and args[0] == "auth"
        if not is_auth_command:
            token_val = self.get_token()
            token_var = self.get_token_env_var()
            if token_val:
                env[token_var] = token_val
        
        if capture_output:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            _logger.info(f"Command executed successfully, output length: {len(result.stdout)} chars")
            _logger.debug(f"Command output: {result.stdout[:200]}...")
            return result.stdout
        else:
            subprocess.run(full_command, check=True, env=env)
            _logger.info("Command executed without capture")
            return ""

    def get_token_env_var(self) -> str:
        """Return appropriate token environment variable based on CLI tool.
        
        Returns:
            Environment variable name for the token.
        """
        return "GITLAB_TOKEN" if self.cli_tool == "glab" else "GITHUB_TOKEN"

    def get_token(self) -> Optional[str]:
        """Get the appropriate token for the configured CLI tool.
        
        Returns:
            Token value or None if not set.
        """
        if self.cli_tool == "glab":
            return config.GITLAB_TOKEN
        return config.GITHUB_TOKEN

    def _convert_glab_command(self, args: List[str]) -> List[str]:
        """Convert GitHub CLI commands to GitLab CLI equivalents."""
        from luma_core.github_project import _convert_glab_command
        return _convert_glab_command(args)


# Global CLI wrapper instance using configured CLI tool
_default_wrapper: Optional[CLIWrapper] = None


def get_cli_wrapper(cli_tool: Optional[str] = None) -> CLIWrapper:
    """Get or create a CLI wrapper instance.
    
    Args:
        cli_tool: Optional CLI tool override. If None, uses config.VCS_CLI.
    
    Returns:
        CLIWrapper instance.
    """
    global _default_wrapper
    
    if cli_tool is None and _default_wrapper is not None:
        return _default_wrapper
    
    wrapper = CLIWrapper(cli_tool)
    
    if cli_tool is None:
        _default_wrapper = wrapper
    
    return wrapper


def run_cli_command(args: List[str], cli_tool: Optional[str] = None, 
                    capture_output: bool = True) -> str:
    """Convenience function to run CLI command with default wrapper.
    
    Args:
        args: List of command arguments.
        cli_tool: Optional CLI tool override.
        capture_output: Whether to capture output.
    
    Returns:
        Command output as string.
    """
    wrapper = get_cli_wrapper(cli_tool)
    return wrapper.run_cli_command(args, capture_output)
