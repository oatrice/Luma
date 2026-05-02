# Implementation Plan: Fix PR creation functionality for GitLab repositories

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**: 
  - `luma_core/platform_detector.py` - Add unified PR functions
  - `luma_core/github_project.py` - Add GraphQL fallback for GitLab
  - `luma_core/actions/admin_actions.py` - Add VCS CLI settings
  - `luma_core/actions/create_issue_action.py` - Add GraphQL fallback
  - `luma_core/config.py` - Fix repository configurations
  - `main.py` - Update PR status checking logic
  - `scripts/deploy_pr.py` - Use unified functions
  - `luma_core/tools.py` - Fix multi-repo PR creation
- **New Components**: 
  - `luma_core/platform_detector.py` - New unified platform detection
- **Dependencies**: 
  - `gh` CLI for GitHub repositories
  - `glab` CLI for GitLab repositories
  - Existing `cli_wrapper.py` for VCS abstraction

### Data Model Changes
```python
# No new data structures required
# Existing LumaState remains compatible
# Configuration updates in PROJECTS and PROJECTS_CANONICAL_VALUES
```

---

## 2. Step-by-Step Implementation

### Step 1: Create Platform Detection Module
- **Docs**: Document platform detection logic
- **Code**: Create `luma_core/platform_detector.py` with unified functions
- **Tests**: Write tests for platform detection from URLs and git remotes

### Step 2: Implement Unified PR Functions
- **Docs**: Document unified PR creation and status checking
- **Code**: Add `create_pull_request_unified()`, `get_open_pr_unified()`, `check_pr_status_unified()`
- **Tests**: Write tests for both GitHub and GitLab scenarios

### Step 3: Fix GraphQL Operations for GitLab
- **Docs**: Document GraphQL fallback behavior
- **Code**: Update `run_gh_graphql()` to handle GitLab CLI gracefully
- **Tests**: Verify GraphQL operations skip correctly for GitLab

### Step 4: Add VCS CLI Settings
- **Docs**: Document VCS CLI configuration
- **Code**: Add settings menu option in `admin_actions.py`
- **Tests**: Verify settings persistence and CLI switching

### Step 5: Update Configuration Files
- **Docs**: Document repository name fixes
- **Code**: Fix `oatrice/Luma` → `oatricedev/Luma` in all configs
- **Tests**: Verify correct repository names are used

### Step 6: Update Scripts and Tools
- **Docs**: Document script updates
- **Code**: Update `deploy_pr.py` and `tools.py` to use unified functions
- **Tests**: Verify scripts work with both platforms

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [ ] Unit Tests: `tests/test_platform_detector.py`
- [ ] Unit Tests: `tests/test_unified_pr.py`
- [ ] Integration Tests: `tests/test_gitlab_integration.py`

### Manual Verification
- [ ] Test PR creation on GitLab repository
- [ ] Test PR status checking on GitLab MR
- [ ] Test Select issue option with GitLab
- [ ] Test VCS CLI settings switching
- [ ] Verify GitHub repositories still work
- [ ] Verify no GraphQL errors with GitLab CLI