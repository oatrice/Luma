"""CLI Wrapper for VCS operations.

This module provides a wrapper for executing VCS CLI commands (gh or glab)
based on the VCS_CLI configuration. It abstracts the differences between
GitHub CLI (gh) and GitLab CLI (glab) commands.
"""

import subprocess
from typing import List, Optional
from luma_core import config


class CLIWrapper:
    """Wrapper for executing VCS CLI commands with configurable tool."""

    def __init__(self, cli_tool: Optional[str] = None):
        """Initialize CLI wrapper with specified CLI tool.
        
        Args:
            cli_tool: The CLI tool to use ("gh" or "glab"). If None, uses
                     config.VCS_CLI (defaults to "gh").
        """
        self.cli_tool = cli_tool or config.VCS_CLI
        
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
        full_command = [self.cli_tool] + args
        
        if capture_output:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        else:
            subprocess.run(full_command, check=True)
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
