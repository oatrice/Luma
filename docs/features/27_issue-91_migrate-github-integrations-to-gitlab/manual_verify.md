# Manual Verification Guide: GitLab CLI Support

> **Feature:** Add GitLab CLI Support (VCS_CLI configuration)
> **Issue:** 91 - Migrate GitHub Integrations to GitLab
> **Date:** 2026-04-30

## Overview

This guide provides step-by-step instructions to manually verify that the VCS_CLI configuration works correctly with both GitHub CLI (`gh`) and GitLab CLI (`glab`).

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated (for GitHub tests)
- GitLab CLI (`glab`) installed and authenticated (for GitLab tests)
- Python environment with Luma installed
- Access to both GitHub and GitLab repositories for testing

## Test Scenarios

### Scenario 1: Default Configuration (Backward Compatibility)

**Objective:** Verify that Luma uses `gh` CLI by default when `VCS_CLI` is not set.

#### Steps

1. Ensure `.env` file does NOT contain `VCS_CLI` (or remove it if present)
2. Ensure `GITHUB_TOKEN` is set in `.env`
3. Run Luma CLI
4. Execute a menu action that uses CLI commands (e.g., List Active Issues)
5. Verify that the command uses `gh` CLI

#### Expected Results

- Luma starts without errors
- CLI commands execute using `gh` (check logs/debug output)
- No errors related to missing CLI configuration

---

### Scenario 2: Explicit GitHub CLI Configuration

**Objective:** Verify that setting `VCS_CLI=gh` explicitly works correctly.

#### Steps

1. Set `VCS_CLI=gh` in `.env`
2. Ensure `GITHUB_TOKEN` is set in `.env`
3. Run Luma CLI
4. Execute a menu action that uses CLI commands
5. Verify that the command uses `gh` CLI

#### Expected Results

- Luma starts without errors
- CLI commands execute using `gh`
- Same behavior as Scenario 1

---

### Scenario 3: GitLab CLI Configuration

**Objective:** Verify that setting `VCS_CLI=glab` works correctly with GitLab.

#### Steps

1. Set `VCS_CLI=glab` in `.env`
2. Ensure `GITLAB_TOKEN` is set in `.env`
3. Run Luma CLI
4. Execute a menu action that uses CLI commands
5. Verify that the command uses `glab` CLI

#### Expected Results

- Luma starts without errors
- CLI commands execute using `glab`
- GitLab-specific commands work correctly

---

### Scenario 4: CLI Wrapper Unit Tests

**Objective:** Verify that all CLI wrapper unit tests pass.

#### Steps

1. Navigate to project root
2. Run: `python3 -m pytest tests/test_cli_wrapper.py -v`

#### Expected Results

- All 15 tests pass
- No test failures or errors

---

### Scenario 5: Issue Metrics with GitHub CLI

**Objective:** Verify issue metrics work with GitHub CLI.

#### Steps

1. Set `VCS_CLI=gh` in `.env`
2. Set `GITHUB_TOKEN` to a valid GitHub token
3. Run Luma CLI
4. Select option to track issue metrics
5. Select a GitHub repository
6. Verify metrics are fetched correctly

#### Expected Results

- Issue metrics are fetched from GitHub
- No errors related to CLI command execution
- Metrics data is displayed correctly

---

### Scenario 6: Issue Metrics with GitLab CLI

**Objective:** Verify issue metrics work with GitLab CLI.

#### Steps

1. Set `VCS_CLI=glab` in `.env`
2. Set `GITLAB_TOKEN` to a valid GitLab token
3. Run Luma CLI
4. Select option to track issue metrics
5. Select a GitLab repository
6. Verify metrics are fetched correctly

#### Expected Results

- Issue metrics are fetched from GitLab
- No errors related to CLI command execution
- Metrics data is displayed correctly

---

### Scenario 7: Admin Actions with GitHub CLI

**Objective:** Verify admin actions work with GitHub CLI.

#### Steps

1. Set `VCS_CLI=gh` in `.env`
2. Set `GITHUB_TOKEN` to a valid GitHub token
3. Run Luma CLI
4. Select Settings (admin) menu
5. Try to list GitHub Projects
6. Verify projects are listed correctly

#### Expected Results

- GitHub Projects are listed
- No errors related to CLI command execution
- Project data is displayed correctly

---

### Scenario 8: Admin Actions with GitLab CLI

**Objective:** Verify admin actions work with GitLab CLI.

#### Steps

1. Set `VCS_CLI=glab` in `.env`
2. Set `GITLAB_TOKEN` to a valid GitLab token
3. Run Luma CLI
4. Select Settings (admin) menu
5. Try to list GitLab projects (if supported)
6. Verify projects are listed correctly

#### Expected Results

- GitLab projects are listed (or appropriate message if not supported)
- No errors related to CLI command execution

---

### Scenario 9: Token Fallback Chain

**Objective:** Verify token fallback chain works correctly.

#### Steps

1. Remove `VCS_TOKEN` from `.env`
2. Set only `GITLAB_TOKEN` in `.env`
3. Set `VCS_CLI=glab`
4. Run Luma CLI
5. Verify that `GITLAB_TOKEN` is used

#### Steps (Alternative)
1. Remove `VCS_TOKEN` and `GITLAB_TOKEN` from `.env`
2. Set only `GITHUB_TOKEN` in `.env`
3. Set `VCS_CLI=gh`
4. Run Luma CLI
5. Verify that `GITHUB_TOKEN` is used

#### Expected Results

- Luma uses the appropriate token based on CLI tool
- No errors related to missing token
- Token fallback chain works as expected

---

### Scenario 10: Error Handling - Invalid CLI Tool

**Objective:** Verify that invalid CLI tool is rejected.

#### Steps

1. Set `VCS_CLI=invalid_cli` in `.env`
2. Run Luma CLI
3. Verify that an error is raised

#### Expected Results

- ValueError is raised with message about invalid VCS_CLI
- Error message is clear and actionable

---

### Scenario 11: Error Handling - CLI Not Found

**Objective:** Verify graceful handling when CLI tool is not installed.

#### Steps

1. Set `VCS_CLI=gh` (or `glab`)
2. Temporarily rename or remove the CLI binary (if safe to do so)
3. Run Luma CLI
4. Execute a CLI command
5. Verify error handling

#### Expected Results

- Appropriate error message is displayed
- Error message suggests installing the CLI tool
- Application does not crash

---

## Quick Verification Checklist

Use this checklist for quick verification:

- [ ] Default configuration works (no VCS_CLI set)
- [ ] Explicit `VCS_CLI=gh` works
- [ ] Explicit `VCS_CLI=glab` works
- [ ] Unit tests pass (15/15)
- [ ] Issue metrics work with gh
- [ ] Issue metrics work with glab
- [ ] Admin actions work with gh
- [ ] Token fallback chain works
- [ ] Invalid CLI tool is rejected
- [ ] Error handling for missing CLI is graceful

---

## Troubleshooting

### Issue: "VCS CLI not found"

**Solution:**
- Install GitHub CLI: `brew install gh` or follow official docs
- Install GitLab CLI: `brew install glab` or follow official docs
- Authenticate: `gh auth login` or `glab auth login`

### Issue: "Invalid VCS_CLI"

**Solution:**
- Ensure `VCS_CLI` is set to either `gh` or `glab`
- Check for typos in `.env` file

### Issue: Token not working

**Solution:**
- Verify token is set in `.env`
- Check token fallback chain: `VCS_TOKEN` → `GITLAB_TOKEN` → `GITHUB_TOKEN`
- Ensure token has appropriate permissions for the CLI tool

---

## Sign-off

| Role | Name | Date | Status |
|------|------|------|--------|
| QA | ___________ | ___________ | ⬜ Pending |
| Tech Lead | ___________ | ___________ | ⬜ Pending |
