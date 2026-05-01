## Problem

Luma is using GitHub API endpoints for GitLab repositories, causing validation errors when creating PRs and GraphQL operations when selecting issues.

**Error 1**: "Failed to create PR: 422 - Validation Failed, field: head, code: invalid"
**Error 2**: "GitLab CLI doesn't support GraphQL operations in this context"
**Error 3**: "Could not get project field schema" when selecting issues

**Root Cause**: 
- Repository URL: https://gitlab.com/oatricedev/Zenith.git (GitLab)
- Luma code uses GitHub API: "https://api.github.com/repos/{owner}/{repo}/pulls"
- GitLab uses different API for merge requests
- GitLab CLI doesn't support GraphQL operations like GitHub CLI
- Kanban sync fails when using GitLab repositories

## Solution Implemented

### 1. Platform Detection
- **File**: `luma_core/platform_detector.py`
- **Function**: `detect_repo_platform()` - Auto-detects GitHub vs GitLab from URLs and git remote
- **Support**: HTTPS, SSH, and owner/repo formats

### 2. Unified PR Creation Functions
- **File**: `luma_core/platform_detector.py`
- **Functions**: 
  - `create_pull_request_unified()` - Routes to appropriate client
  - `get_open_pr_unified()` - Checks existing PRs/MRs
  - `update_pull_request_unified()` - Updates existing PRs/MRs

### 3. Updated Scripts
- **File**: `scripts/deploy_pr.py` - Now uses unified functions
- **File**: `luma_core/tools.py` - Multi-repo PR creation fixed

### 4. PR Status Checking Fix
- **Problem**: "Invalid PR URL" error when checking GitLab MR status
- **Solution**: `check_pr_status_unified()` function
- **File**: `luma_core/platform_detector.py`
- **Updated**: `main.py` now uses unified status checking
- **Support**: Both GitHub PRs and GitLab MRs
- **Example**: MR #91 https://gitlab.com/oatricedev/Luma/-/merge_requests/91

### 5. GraphQL Operations Fallback (NEW)
- **Problem**: "GitLab CLI doesn't support GraphQL operations in this context"
- **Problem**: "Could not get project field schema" when selecting issues
- **Solution**: Added fallback handling for GitLab CLI in GraphQL operations
- **Files**: 
  - `luma_core/github_project.py` - Updated `run_gh_graphql()`, `get_project_field_schema()`, `update_item_status()`
  - `luma_core/actions/create_issue_action.py` - Updated `add_issue_to_project()`
- **Behavior**: GitLab CLI gracefully skips GraphQL operations with clear messages
- **Support**: Select issue option now works with GitLab repositories

### 6. VCS CLI Settings (NEW)
- **Problem**: User couldn't easily switch between gh/glab CLI tools
- **Solution**: Added VCS CLI option in Luma Settings menu
- **File**: `luma_core/actions/admin_actions.py` - Added option [3] VCS CLI
- **Features**: User-friendly interface to select GitHub CLI or GitLab CLI
- **Persistence**: Settings saved in `.luma_global.json`

### 7. Authentication
- **GitHub**: Uses `gh` CLI with GITHUB_TOKEN
- **GitLab**: Uses `glab` CLI with GITLAB_TOKEN
- **Existing**: `cli_wrapper.py` handles both platforms

## Implementation Status

- [x] Platform detection logic
- [x] Unified PR creation functions  
- [x] Updated deploy_pr.py script
- [x] Updated tools.py for multi-repo PRs
- [x] PR status checking unified function
- [x] Updated main.py for status checking
- [x] GraphQL operations fallback for GitLab
- [x] VCS CLI settings option in menu
- [x] Fixed Select issue option for GitLab
- [x] Error handling improvements
- [x] Testing and verification

## Testing

- **Test Files**: `test_pr_creation.py`, `test_pr_status_fix.py`
- **Verified**: Platform detection works correctly
- **Verified**: PR creation works for both platforms
- **Verified**: PR status checking works for both platforms
- **Verified**: GraphQL fallback works for GitLab CLI
- **Verified**: Select issue option works with GitLab repositories
- **Verified**: VCS CLI settings menu works correctly
- **Example**: MR #91 https://gitlab.com/oatricedev/Luma/-/merge_requests/91

## Files Modified

- `luma_core/platform_detector.py` (NEW)
- `scripts/deploy_pr.py` (UPDATED)
- `luma_core/tools.py` (UPDATED) 
- `main.py` (UPDATED)
- `luma_core/github_project.py` (UPDATED) - GraphQL fallback
- `luma_core/actions/admin_actions.py` (UPDATED) - VCS CLI settings
- `luma_core/actions/create_issue_action.py` (UPDATED) - GraphQL fallback
- `luma_core/config.py` (UPDATED) - Configuration fixes

## Result

✅ **FIXED**: Luma now correctly creates and checks PRs for GitLab repositories
✅ **FIXED**: No more "Invalid PR URL" errors for GitLab MRs
✅ **FIXED**: No more "GitLab CLI doesn't support GraphQL operations" errors
✅ **FIXED**: Select issue option now works with GitLab repositories
✅ **FIXED**: VCS CLI settings menu allows easy switching between gh/glab
✅ **COMPATIBLE**: GitHub repositories continue to work as before
✅ **AUTOMATIC**: Platform detection works seamlessly
✅ **USER-FRIENDLY**: Clear error messages and graceful fallbacks

The original errors for GitLab repositories are now completely resolved:
- "Failed to create PR: 422 - Validation Failed, field: head, code: invalid"
- "GitLab CLI doesn't support GraphQL operations in this context"
- "Could not get project field schema"
