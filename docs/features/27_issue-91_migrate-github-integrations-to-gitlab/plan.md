# Implementation Plan: Add GitLab CLI Support

> **Refers to**: [Spec Link](./spec.md)

> **Status**: Approved

## 1. Architecture & Design

*High-level technical approach.*

### Component View

#### New Components

- **`luma_core/cli_wrapper.py`** - New CLI command wrapper
  - `CLIWrapper` class to abstract CLI command execution
  - Methods for running CLI commands with configured tool
  - Token environment variable mapping

#### Modified Components

- **`luma_core/config.py`** - Add VCS_CLI configuration option
- **`luma_core/issue_metrics.py`** - Update to use CLI wrapper
- **`luma_core/actions/create_issue_action.py`** - Update to use CLI wrapper
- **`luma_core/actions/admin_actions.py`** - Update to use CLI wrapper
- **`luma_core/actions/metrics_actions.py`** - Update to use CLI wrapper
- **`.env.example`** - Add VCS_CLI configuration example

#### Dependencies

- Existing: `KanbanCard`, `IssueData`, `safe_input` utilities
- New: `glab` CLI (GitLab command-line tool) - user must install

### Data Model Changes

No data model changes required. Existing `IssueData` and state management will continue to work as before.

---

## 2. Step-by-Step Implementation

### Phase 1: Configuration and CLI Wrapper

#### Step 1.1: Add VCS_CLI Configuration

- **Docs**: Update configuration documentation
- **Code**: Modify `luma_core/config.py`:
  - Add `VCS_CLI` config option with default value "gh"
  - Add `VCS_TOKEN` with fallbacks to `GITLAB_TOKEN` and `GITHUB_TOKEN`
- **Code**: Update `.env.example` with VCS_CLI example
- **Tests**: Verify configuration loading with default and custom values

#### Step 1.2: Create CLI Wrapper

- **Docs**: Document CLI wrapper interface and usage
- **Code**: Implement `CLIWrapper` class in `luma_core/cli_wrapper.py`:
  - `run_cli_command(command: str, args: List[str]) -> str` - Execute command using configured CLI
  - `get_token_env_var() -> str` - Return appropriate token env var based on CLI
  - Handle command execution errors gracefully
- **Tests**: Unit tests for CLI wrapper with both gh and glab

---

### Phase 2: Update CLI Command Usage

#### Step 2.1: Update Issue Metrics Actions

- **Docs**: Document CLI command changes for issue metrics
- **Code**: Update `luma_core/issue_metrics.py`:
  - Replace direct `gh issue list` calls with CLI wrapper
  - Replace direct `gh api` calls with CLI wrapper
  - Map command arguments between gh and glab syntax
- **Tests**: Unit tests for issue metrics with both CLIs

#### Step 2.2: Update Create Issue Actions

- **Docs**: Document CLI command changes for issue creation
- **Code**: Update `luma_core/actions/create_issue_action.py`:
  - Replace direct `gh issue create` calls with CLI wrapper
  - Map command arguments between gh and glab syntax
- **Tests**: Unit tests for create issue with both CLIs

#### Step 2.3: Update Admin Actions

- **Docs**: Document CLI command changes for admin actions
- **Code**: Update `luma_core/actions/admin_actions.py`:
  - Replace GraphQL via `gh api` with CLI wrapper
  - Map command arguments between gh and glab syntax
- **Tests**: Unit tests for admin actions with both CLIs

#### Step 2.4: Update Metrics Actions

- **Docs**: Document CLI command changes for metrics actions
- **Code**: Update `luma_core/actions/metrics_actions.py`:
  - Replace direct `gh issue list` calls with CLI wrapper
  - Map command arguments between gh and glab syntax
- **Tests**: Unit tests for metrics actions with both CLIs

---

### Phase 3: Testing and Documentation

#### Step 3.1: Unit Tests

- **Code**: Create unit tests for CLI wrapper
- **Code**: Test CLI wrapper with gh commands
- **Code**: Test CLI wrapper with glab commands
- **Code**: Test token environment variable mapping
- **Code**: Update existing tests to work with both CLIs
- **Tests**: All unit tests pass with both gh and glab

#### Step 3.2: Integration Tests

- **Code**: Test issue metrics with gh CLI
- **Code**: Test issue metrics with glab CLI
- **Code**: Test create issue with gh CLI
- **Code**: Test create issue with glab CLI
- **Code**: Test admin actions with gh CLI
- **Code**: Test admin actions with glab CLI
- **Tests**: All integration tests pass

#### Step 3.3: Manual Verification

- **Manual**: Test with VCS_CLI=gh (default)
- **Manual**: Test with VCS_CLI=glab
- **Manual**: Test backward compatibility (no VCS_CLI set)
- **Manual**: Test error handling for missing tokens
- **Manual**: Test CLI command syntax mapping

#### Step 3.4: Documentation

- **Docs**: Update README.md with VCS_CLI configuration
- **Docs**: Update .env.example with VCS_CLI example
- **Docs**: Create CLI configuration guide
- **Docs**: Document glab installation requirements

---

## 3. Verification Plan

*How will we verify success?*

### Automated Tests

- [ ] Unit Tests: CLI wrapper tests pass
- [ ] Integration Tests: Both gh and glab integrations work
- [ ] Regression Tests: Existing functionality not broken

### Manual Verification

- [ ] gh CLI works with VCS_CLI=gh or not set
- [ ] glab CLI works with VCS_CLI=glab
- [ ] Issue metrics work with both CLIs
- [ ] Create issue works with both CLIs
- [ ] Admin actions work with both CLIs
- [ ] Metrics actions work with both CLIs
- [ ] Backward compatibility maintained

### Acceptance Criteria Checklist

- [ ] VCS_CLI configuration option added to config.py
- [ ] Default value is "gh" for backward compatibility
- [ ] CLI wrapper created to abstract CLI command execution
- [ ] All `gh` CLI calls updated to use CLI wrapper
- [ ] `glab` CLI commands work when VCS_CLI=glab
- [ ] `gh` CLI commands continue to work when VCS_CLI=gh or not set
- [ ] Token environment variable mapping works correctly
- [ ] Issue metrics actions work with both CLIs
- [ ] Create issue actions work with both CLIs
- [ ] Admin actions work with both CLIs
- [ ] Documentation updated with CLI configuration instructions
- [ ] Tests pass with both `gh` and `glab`

---

## 4. Rollout Plan

### Deployment Strategy

1. **Default Configuration**: Deploy with VCS_CLI defaulting to "gh"
2. **Documentation**: Update documentation with VCS_CLI configuration instructions
3. **User Adoption**: Users can set VCS_CLI=glab to use GitLab CLI
4. **No Breaking Changes**: Existing users continue to use gh without changes

### Migration Timeline

- **Day 1**: Phase 1 - Configuration and CLI Wrapper
- **Day 2**: Phase 2 - Update CLI Command Usage (Steps 2.1-2.4)
- **Day 3**: Phase 3 - Testing and Documentation

### Rollback Plan

- Revert config.py changes if needed
- Remove CLI wrapper and revert to direct gh calls if needed
- Document rollback procedure

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CLI command syntax differences between gh and glab | Map CLI commands carefully, test both tools |
| Output format differences between CLIs | Parse output flexibly, handle both formats |
| Token environment variable confusion | Clear documentation, use appropriate token based on CLI |
| Breaking existing GitHub workflows | Maintain backward compatibility with gh as default |
| glab CLI not installed by users | Document glab installation requirements clearly |
