# Specification: Migrate GitHub Integrations to GitLab

> **Status**: Approved

> **Owner**: Kilo

> **Dates**: Created: 2026-04-29 | Last Updated: 2026-04-29

## 1. Context & Goal

*Why are we building this? What is the problem statement?*

### Problem

Luma repository has been migrated from GitHub to GitLab, but the codebase still contains GitHub-specific CLI commands (`gh`). Users working with GitLab repositories need to use GitLab CLI (`glab`) instead of GitHub CLI (`gh`). Currently, there is no way to configure which CLI tool to use.

### Goal

Add configuration option to allow users to select between GitHub CLI (`gh`) and GitLab CLI (`glab`) for VCS operations. Maintain backward compatibility by keeping `gh` as the default, while enabling `glab` support for GitLab repositories.

---

## 2. User Journey & Requirements

*What should the user experience?*

### User Story

As a **developer working with GitLab repositories**, I want to **configure Luma to use GitLab CLI (`glab`) instead of GitHub CLI (`gh`)**, so that **I can use Luma with GitLab repositories without being forced to use GitHub tools**.

### Functional Requirements

- [ ] Add `VCS_CLI` configuration option (default: "gh")
- [ ] Support "gh" (GitHub CLI) and "glab" (GitLab CLI) values
- [ ] Update all CLI command executions to use configured CLI tool
- [ ] Maintain backward compatibility with `gh` as default
- [ ] Add documentation for CLI configuration
- [ ] Update issue metrics actions to use configured CLI
- [ ] Update create issue actions to use configured CLI
- [ ] Update admin actions to use configured CLI

### Non-Functional Requirements

- [ ] Performance: CLI command execution should not be affected
- [ ] Reliability: CLI switching should not crash the system
- [ ] Usability: Configuration should be easy to understand
- [ ] Maintainability: CLI abstraction should be easy to extend
- [ ] Security: Token management remains secure (GITHUB_TOKEN or GITLAB_TOKEN)

---

## 3. Specification by Example (SBE)

*Concrete examples of behavior.*

### Scenario: Configure GitLab CLI

**Given** user has `VCS_CLI=glab` set in environment

**When** user runs Luma

**Then** all CLI operations use `glab` instead of `gh`

**And** appropriate tokens (GITLAB_TOKEN) are used

#### Examples

| VCS_CLI | Token | CLI Used |
|---------|-------|----------|
| gh | GITHUB_TOKEN | gh CLI |
| glab | GITLAB_TOKEN | glab CLI |
| (not set) | GITHUB_TOKEN | gh CLI (default) |
| (not set) | GITLAB_TOKEN | gh CLI (default, may fail) |

---

### Scenario: Create Issue with GitLab CLI

**Given** user has `VCS_CLI=glab` configured

**When** user selects "Create New Issue" from menu

**And** enters issue details

**Then** issue is created using `glab issue create`

**And** issue URL is displayed

#### Examples

| VCS_CLI | Command | Result |
|---------|---------|--------|
| gh | gh issue create | GitHub issue created |
| glab | glab issue create | GitLab issue created |

---

### Scenario: List Issues with GitLab CLI

**Given** user has `VCS_CLI=glab` configured

**When** user selects "List Active Issues" from menu

**Then** issues are fetched using `glab issue list`

**And** issues are displayed

#### Examples

| VCS_CLI | Command | Result |
|---------|---------|--------|
| gh | gh issue list | GitHub issues listed |
| glab | glab issue list | GitLab issues listed |

---

### Scenario: Backward Compatibility with GitHub CLI

**Given** user has not set `VCS_CLI`

**When** user runs Luma

**Then** `gh` CLI is used by default

**And** all existing functionality continues to work

#### Examples

| Scenario | VCS_CLI | Expected Behavior |
|----------|---------|-------------------|
| Existing setup | (not set) | Uses gh CLI (backward compatible) |
| New GitLab setup | glab | Uses glab CLI |
| Explicit GitHub | gh | Uses gh CLI |

---

## 4. Constraints & Risks

*What should we watch out for?*

### Constraints

- Must maintain backward compatibility with `gh` as default
- Must not break existing workflows
- Must support both `gh` and `glab` CLI tools
- Must handle CLI-specific differences (command syntax, output format)

### Risks

- **Risk:** CLI command syntax differences between `gh` and `glab`
  - **Mitigation:** Map CLI commands carefully, test both tools

- **Risk:** Output format differences between CLIs
  - **Mitigation:** Parse output flexibly, handle both formats

- **Risk:** Token environment variable confusion
  - **Mitigation:** Clear documentation, use appropriate token based on CLI

---

## 5. Architecture Overview

### CLI Abstraction Pattern

```
luma_core/
  config.py           # Add VCS_CLI configuration
  cli_wrapper.py      # New: CLI command wrapper
  actions/
    issue_actions.py   # Use cli_wrapper for CLI commands
    create_issue_action.py  # Use cli_wrapper for CLI commands
    admin_actions.py   # Use cli_wrapper for CLI commands
    metrics_actions.py # Use cli_wrapper for CLI commands
```

### Key Configuration

```python
# config.py
VCS_CLI = os.getenv("VCS_CLI", "gh")  # "gh" or "glab"
VCS_TOKEN = os.getenv("VCS_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GITLAB_TOKEN")
```

### CLI Wrapper Interface

```python
class CLIWrapper:
    def run_cli_command(self, command: str, args: List[str]) -> str:
        """Execute command using configured CLI (gh or glab)"""
        cli = config.VCS_CLI
        full_command = [cli] + args
        # Execute and return output
    
    def get_token_env_var(self) -> str:
        """Return appropriate token env var based on CLI"""
        return "GITLAB_TOKEN" if config.VCS_CLI == "glab" else "GITHUB_TOKEN"
```

---

## 6. Acceptance Criteria

- [ ] `VCS_CLI` configuration option added to config.py
- [ ] Default value is "gh" for backward compatibility
- [ ] CLI wrapper created to abstract CLI command execution
- [ ] All `gh` CLI calls updated to use CLI wrapper
- [ ] `glab` CLI commands work when `VCS_CLI=glab`
- [ ] `gh` CLI commands continue to work when `VCS_CLI=gh` or not set
- [ ] Token environment variable mapping works correctly
- [ ] Issue metrics actions work with both CLIs
- [ ] Create issue actions work with both CLIs
- [ ] Admin actions work with both CLIs
- [ ] Documentation updated with CLI configuration instructions
- [ ] Tests pass with both `gh` and `glab`
