# SBE (Software Behavior Example): Enable Add/Remove Issue Menu Options in All Workflow Phases

## Behavior Overview

This document describes the expected and implemented behavior for enabling add/remove issue menu options to work in all workflow phases of the Luma system.

## User Story

**As a** Luma user  
**I want to** add and remove issues from my active session regardless of which workflow phase I'm currently in  
**So that** I can manage my work items efficiently without having to switch phases just for issue management

## Expected Behaviors

### 1. Menu Visibility

**Given** I am in any workflow phase (IDLE, SELECTING, CODING, REVIEWING, PREFLIGHT, PR_PENDING)  
**When** I view the interactive menu  
**Then** I should see both "+" (Add Issue) and "-" (Remove Issue) options

**Implementation Status**: ✅ COMPLETED
- Updated `MENU_ACTIONS` in `main.py` to use `"valid_phases": "ALL"`

### 2. Add Issue Functionality

**Given** I am in any workflow phase  
**When** I select the "+" option  
**Then** I should be able to:
- See a list of available issues from Kanban
- Select one or more issues to add to my active session
- Receive confirmation that issues were added successfully
- See the updated list of active issues

**Implementation Status**: ✅ COMPLETED
- Removed phase restriction from `action_add_issue()` function
- Function now works in all phases without validation

### 3. Remove Issue Functionality

**Given** I have multiple active issues in my session  
**When** I select the "-" option  
**Then** I should be able to:
- See a list of my current active issues
- Select one or more issues to remove (keeping at least 1)
- Receive confirmation that issues were removed successfully
- See the updated list of remaining active issues

**Implementation Status**: ✅ COMPLETED
- `action_remove_issue()` already had no phase restrictions
- Function works consistently across all phases

## Behavior Examples

### Example 1: Adding Issues in IDLE Phase

**Scenario**: User starts Luma and is in IDLE phase, wants to add issues before starting work

**Before Implementation**:
```
📍 Phase  : 💤 IDLE
👉 Select an action:
[0] ❌ Exit
[1] 📋 List Active Issues
[2] 📥 Select Issue (from Kanban)
[N] 🆕 Create New Issue
// Note: + and - options NOT visible
```

**After Implementation**:
```
📍 Phase  : 💤 IDLE
👉 Select an action:
[0] ❌ Exit
[1] 📋 List Active Issues
[2] 📥 Select Issue (from Kanban)
[+] ➕ Add Issue (to session)          // ✅ Now visible
[-] ➖ Remove Issue (from session)     // ✅ Now visible
[N] 🆕 Create New Issue
```

**User Action**: Selects "+"
**System Response**: Shows available issues from Kanban, allows selection, adds to active session

### Example 2: Removing Issues in REVIEWING Phase

**Scenario**: User is in REVIEWING phase with 3 active issues, wants to focus on just 1

**Before Implementation**:
```
📍 Phase  : 👀 REVIEWING
👉 Select an action:
[0] ❌ Exit
[6] 🧐 Code Review (Local)
[7] 📝 Update Docs
// Note: - option NOT visible, user stuck with all 3 issues
```

**After Implementation**:
```
📍 Phase  : 👀 REVIEWING
👉 Select an action:
[0] ❌ Exit
[6] 🧐 Code Review (Local)
[7] 📝 Update Docs
[+] ➕ Add Issue (to session)
[-] ➖ Remove Issue (from session)     // ✅ Now visible
```

**User Action**: Selects "-", chooses 2 issues to remove
**System Response**: Removes selected issues, keeps 1 primary issue, confirms success

## Edge Cases and Error Handling

### 1. No Active Issues to Remove

**Behavior**: If user tries to remove issues but has only 1 active issue
**Expected**: System displays "Cannot remove: need at least 1 active issue."
**Implementation Status**: ✅ Already handled

### 2. No Available Issues to Add

**Behavior**: If user tries to add issues but no additional issues available
**Expected**: System displays "📬 No additional issues available."
**Implementation Status**: ✅ Already handled

### 3. Invalid Selection

**Behavior**: If user enters invalid issue numbers
**Expected**: System displays validation error and allows retry
**Implementation Status**: ✅ Already handled

## Technical Implementation Details

### Phase Validation Removal

**Code Change**:
```python
# REMOVED from action_add_issue():
if state.phase not in [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]:
    print("❌ Can only add issues during CODING or PREFLIGHT phase.")
    return False
```

**Impact**: Function now executes in all phases without early termination

### Menu Configuration Update

**Code Change**:
```python
# UPDATED in main.py MENU_ACTIONS:
"+": {"label": "➕ Add Issue (to session)", "valid_phases": "ALL"},
"-": {"label": "➖ Remove Issue (from session)", "valid_phases": "ALL"},
```

**Impact**: Menu options appear and are selectable in all phases

## Testing Scenarios

### Test Case 1: Menu Visibility Across Phases
1. Start Luma in IDLE phase → Verify + and - options visible
2. Transition to SELECTING phase → Verify + and - options visible  
3. Transition to CODING phase → Verify + and - options visible (existing)
4. Transition to REVIEWING phase → Verify + and - options visible
5. Transition to PREFLIGHT phase → Verify + and - options visible (existing)
6. Transition to PR_PENDING phase → Verify + and - options visible

### Test Case 2: Add Issue Functionality
1. In any phase, select "+" option
2. Verify issue list displays correctly
3. Select valid issue(s)
4. Verify confirmation message
5. Verify active issues list updates

### Test Case 3: Remove Issue Functionality  
1. With multiple active issues, select "-" option
2. Verify current issues list displays
3. Select valid issue(s) to remove (keeping at least 1)
4. Verify confirmation message
5. Verify remaining issues list updates

## Performance Considerations

- **No additional overhead**: Removing phase checks actually reduces validation
- **Menu rendering**: No impact on menu display performance
- **Issue fetching**: Existing Kanban fetching logic unchanged
- **State management**: No additional state complexity introduced

## Related Issues and Fixes

### Infrastructure Fixes Implemented
During the implementation and testing of this feature, several related infrastructure issues were identified and resolved:

#### Issue #95: VCS_CLI Configuration Support
- **Problem**: Roadmap update fallback used hardcoded "gh" CLI instead of configured VCS_CLI
- **Fix**: Updated quality_actions.py to use get_cli_wrapper().cli_tool for proper GitLab support
- **Impact**: Enables roadmap operations with GitLab CLI (glab)

#### Issue #96: VCS Repo Detection Enhancement ✅
- **Problem**: Repo detection only worked for GitHub repositories
- **Fix**: Extended _detect_repo_and_kanban to support GitLab URLs
- **Impact**: Correct repo name detection for GitLab projects (e.g., oatricedev/Cerebro vs oatrice/Cerebro)

#### Issue #97: GitLab CLI Field Compatibility ✅
- **Problem**: sync_github_metrics_for_project used GitHub-specific fields (projectItems, stateReason) not available in GitLab CLI
- **Fix**: Added platform detection and conditional field handling
  - GitHub: uses `projectItems` and `stateReason` fields
  - GitLab: uses `state` field, no `projectItems` support
  - Added status mapping for GitLab states (opened→🟡 In Progress, closed→✅ Complete)
- **Impact**: GitLab CLI metrics sync now works without field errors

### Testing with Fixes
- Verified feature works correctly in GitLab environment
- Confirmed CLI tool selection based on VCS_CLI configuration
- Validated repo detection across different VCS platforms

## User Experience Improvements

1. **Reduced Friction**: No need to switch phases for issue management
2. **Consistent Interface**: Add/remove behavior same across all phases
3. **Workflow Continuity**: Users can stay focused on current task
4. **Mental Model Simplification**: Fewer rules to remember
5. **Cross-Platform Support**: Seamless operation with GitHub and GitLab repositories

## Conclusion

The implementation successfully addresses all expected behaviors with minimal code changes. Users can now manage their active issues consistently across all workflow phases, improving the overall user experience and workflow efficiency. Additionally, related infrastructure improvements ensure robust support across different version control platforms.