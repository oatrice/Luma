# Specification: Enable Add/Remove Issue Menu Options in All Workflow Phases

## Feature Specification

**Feature ID**: 30  
**Issue Numbers**: 94, 95, 96, 97  
**Status**: ✅ IMPLEMENTED  
**Implementation Date**: 2026-05-05  

## Objective

Enable the add (`+`) and remove (`-`) issue menu options to function in all workflow phases of the Luma system, removing the previous restriction to only CODING and PREFLIGHT phases.

## Requirements

### Functional Requirements

#### FR-1: Universal Menu Visibility
- **Description**: Add and remove issue options shall be visible in the interactive menu for all workflow phases
- **Phases Affected**: IDLE, SELECTING, CODING, REVIEWING, PREFLIGHT, PR_PENDING
- **Priority**: High
- **Status**: ✅ IMPLEMENTED

#### FR-2: Cross-Phase Add Functionality  
- **Description**: Users shall be able to add issues to their active session from any workflow phase
- **Pre-conditions**: User has access to Kanban, there are available issues not already in active session
- **Post-conditions**: Selected issues are added to active_issues list, confirmation displayed
- **Priority**: High
- **Status**: ✅ IMPLEMENTED

#### FR-3: Cross-Phase Remove Functionality
- **Description**: Users shall be able to remove issues from their active session from any workflow phase
- **Pre-conditions**: User has 2+ active issues in session
- **Post-conditions**: Selected issues are removed from active_issues list (minimum 1 remains), confirmation displayed
- **Priority**: High
- **Status**: ✅ IMPLEMENTED

### Non-Functional Requirements

#### NFR-1: Performance
- **Requirement**: No performance degradation for menu rendering or issue operations
- **Target**: <100ms response time for menu operations
- **Status**: ✅ MET (Removed validation actually improves performance)

#### NFR-2: Backward Compatibility
- **Requirement**: Existing functionality in CODING and PREFLIGHT phases must remain unchanged
- **Status**: ✅ MET (No breaking changes introduced)

#### NFR-3: User Experience
- **Requirement**: Consistent behavior across all phases
- **Status**: ✅ MET (Same UI/UX patterns used throughout)

## Technical Specification

### System Architecture Changes

#### Component: luma_core/actions/issue_actions.py
```python
# FUNCTION: action_add_issue()
# CHANGE: Removed phase restriction validation
# IMPACT: Function now executes in all phases

# BEFORE:
if state.phase not in [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]:
    print("❌ Can only add issues during CODING or PREFLIGHT phase.")
    return False

# AFTER: (validation removed)
```

#### Component: main.py
```python
# COMPONENT: MENU_ACTIONS dictionary
# CHANGE: Updated valid_phases configuration
# IMPACT: Menu options visible in all phases

# BEFORE:
"+": {"label": "➕ Add Issue (to session)", "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]},
"-": {"label": "➖ Remove Issue (from session)", "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]},

# AFTER:
"+": {"label": "➕ Add Issue (to session)", "valid_phases": "ALL"},
"-": {"label": "➖ Remove Issue (from session)", "valid_phases": "ALL"},
```

### Data Flow

#### Add Issue Flow
1. User selects "+" option from menu
2. System calls `action_add_issue(state, project)`
3. Function fetches available Kanban issues
4. User selects issue(s) to add
5. System validates and adds to `state.active_issues`
6. Confirmation message displayed
7. State saved to disk

#### Remove Issue Flow
1. User selects "-" option from menu
2. System calls `action_remove_issue(state, project)`
3. Function displays current `state.active_issues`
4. User selects issue(s) to remove (minimum 1 must remain)
5. System validates and removes from `state.active_issues`
6. Confirmation message displayed
7. State saved to disk

### API Specifications

#### action_add_issue()
```python
def action_add_issue(state: LumaState, project: dict) -> bool:
    """Add an issue to the current active issues (mid-work)"""
    
    # Parameters:
    # - state: Current LumaState object
    # - project: Project configuration dictionary
    
    # Returns:
    # - bool: True if successful, False otherwise
    
    # Behavior:
    # 1. Display current active issues (if any)
    # 2. Fetch available issues from Kanban
    # 3. Filter out already active issues
    # 4. Display selection interface
    # 5. Parse user selection (multi-select supported)
    # 6. Add selected issues to state.active_issues
    # 7. Sync with Kanban if applicable
    # 8. Display confirmation
    
    # Phase Restrictions: None (works in all phases)
```

#### action_remove_issue()
```python
def action_remove_issue(state: LumaState, project: dict) -> bool:
    """Remove an issue from the current active issues"""
    
    # Parameters:
    # - state: Current LumaState object  
    # - project: Project configuration dictionary
    
    # Returns:
    # - bool: True if successful, False otherwise
    
    # Behavior:
    # 1. Validate at least 2 active issues exist
    # 2. Display current active issues with primary indicator
    # 3. Display selection interface
    # 4. Parse user selection (multi-select supported)
    # 5. Validate removal won't leave zero issues
    # 6. Remove selected issues from state.active_issues
    # 7. Display confirmation
    
    # Phase Restrictions: None (works in all phases)
```

## User Interface Specification

### Menu Integration

#### Menu Option Labels
- **Add Issue**: "➕ Add Issue (to session)"
- **Remove Issue**: "➖ Remove Issue (from session)"

#### Menu Keys
- **Add**: "+" key
- **Remove**: "-" key

#### Menu Visibility Rules
```python
"valid_phases": "ALL"  # Visible in all phases
```

### Interaction Patterns

#### Add Issue Interaction
1. User presses "+" key
2. System displays: "➕ Add Issue to Current Work Session"
3. Shows current active issues (if any)
4. Lists available issues from Kanban with format: "[#] Issue Number: Title (Status)"
5. User enters selection (supports comma-separated multi-select)
6. System processes and confirms

#### Remove Issue Interaction
1. User presses "-" key  
2. System displays: "- Remove Issue from Current Work Session"
3. Lists current active issues with primary indicator
4. User enters selection (supports comma-separated multi-select)
5. System validates minimum 1 issue remains
6. System processes and confirms

## Testing Specification

### Test Cases

#### TC-01: Menu Visibility Test
**Objective**: Verify add/remove options appear in all phases
**Test Steps**:
1. Start Luma in IDLE phase
2. Verify "+" and "-" options visible
3. Transition through each phase (SELECTING, CODING, REVIEWING, PREFLIGHT, PR_PENDING)
4. Verify options remain visible in each phase
**Expected Result**: Options visible in all phases

#### TC-02: Add Issue Functionality Test
**Objective**: Verify add functionality works in all phases
**Test Steps**:
1. In each phase, select "+" option
2. Verify issue list displays correctly
3. Select valid issue to add
4. Verify confirmation and state update
**Expected Result**: Function works consistently across all phases

#### TC-03: Remove Issue Functionality Test
**Objective**: Verify remove functionality works in all phases
**Test Steps**:
1. Setup: Have 2+ active issues
2. In each phase, select "-" option
3. Verify current issues list displays
4. Select issue to remove (keeping at least 1)
5. Verify confirmation and state update
**Expected Result**: Function works consistently across all phases

#### TC-04: Edge Cases Test
**Objective**: Verify error handling works correctly
**Test Steps**:
1. Try to remove with only 1 active issue
2. Try to add when no additional issues available
3. Try invalid selections
**Expected Result**: Appropriate error messages displayed

### Performance Tests

#### PT-01: Menu Rendering
**Objective**: Verify no performance degradation
**Test**: Measure menu display time before and after changes
**Target**: <100ms for menu rendering

#### PT-02: Issue Operations
**Objective**: Verify issue operation performance
**Test**: Measure add/remove operation times
**Target**: <500ms for issue operations

## Implementation Details

### Code Changes Summary

| File | Lines Changed | Change Type | Impact |
|------|---------------|--------------|--------|
| luma_core/actions/issue_actions.py | 4 removed | Feature enhancement | Removes phase restriction |
| main.py | 2 changed | Configuration update | Enables menu visibility |
| luma_core/issue_metrics.py | ~30 modified | Bug fix | GitLab CLI field compatibility (Issue #97) |

### Dependencies
- No new dependencies introduced
- No existing dependencies modified
- No external API changes required

### Migration Considerations
- No data migration required
- No configuration migration required
- Changes are backward compatible

## Risk Assessment

### Technical Risks
- **Risk**: Low (removing restrictions is generally safe)
- **Mitigation**: Comprehensive testing across all phases
- **Impact**: Minimal (no breaking changes)

### User Experience Risks
- **Risk**: Very Low (improves user experience)
- **Mitigation**: Clear error messages and consistent behavior
- **Impact**: Positive (reduces friction)

## Acceptance Criteria

### Functional Acceptance
- [x] Add/remove options visible in all workflow phases
- [x] Add functionality works in all phases
- [x] Remove functionality works in all phases
- [x] No regression in existing functionality
- [x] Error handling works correctly

### Non-Functional Acceptance
- [x] No performance degradation
- [x] Backward compatibility maintained
- [x] Consistent user experience across phases
- [x] Code quality standards met

## Deployment Information

### Release Notes
```
Feature: Enable add/remove issue menu options in all workflow phases

- Users can now add and remove issues from any workflow phase
- Menu options (+ and -) are now visible in IDLE, SELECTING, REVIEWING, and PR_PENDING phases
- No breaking changes - existing functionality preserved
- Improved workflow flexibility and user experience
```

### Rollback Plan
If rollback is required:
1. Restore phase validation in `action_add_issue()`
2. Restore menu configuration in `main.py`
3. Test rollback in staging environment
4. Deploy rollback to production

## Related Issues

### Issues Addressed in Implementation
1. **Issue #94**: Enable Add/Remove Issue Menu Options in All Workflow Phases (this feature)
2. **Issue #95**: Fix VCS_CLI configuration support in roadmap update fallback (GitLab CLI support)
3. **Issue #96**: Fix VCS repo detection to support GitLab repos (repo name detection fix)
4. **Issue #97**: Fix GitLab CLI issue list fields mismatch in sync_github_metrics

### Additional Context
- Issues #95, #96, and #97 were identified and fixed during the implementation and testing of this feature
- These fixes ensure proper CLI tool support, repo detection, and field compatibility for GitLab-based projects
- The fixes are backward compatible and don't affect the core functionality of this feature

## Future Enhancements

### Potential Improvements
1. **Bulk Operations**: Enhanced multi-select interface
2. **Issue Reordering**: Ability to reorder active issues
3. **Session Persistence**: Save issue sessions across restarts
4. **Smart Suggestions**: AI-powered issue recommendations

### Related Features
1. **Phase-Aware Actions**: Consider phase-specific behavior for other menu options
2. **Workflow Optimization**: Analyze and optimize other phase restrictions
3. **User Preferences**: Allow users to customize menu visibility

## Conclusion

This feature has been successfully implemented with minimal code changes and no breaking changes. The specification requirements have been fully met, providing users with the flexibility to manage issues across all workflow phases while maintaining system stability and performance.