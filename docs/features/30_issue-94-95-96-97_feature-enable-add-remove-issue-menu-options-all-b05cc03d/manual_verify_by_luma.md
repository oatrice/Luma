# Manual Verification Guide: Enable Add/Remove Issue Options in All Phases + VCS Fixes

## 1. Testing Add/Remove Issue Menu Options

### Step 1: Start Luma Interactive Mode
Run `python3 ../../Luma/main.py` from worktree directory
Navigate to ensure you're in IDLE phase (should show by default)

### Step 2: Verify Menu Options Visibility in IDLE Phase
Look at the interactive menu options
Check that "+" (➕ Add Issue) and "-" (➖ Remove Issue) are visible

### Expected Result: 
Both + and - options should appear in the menu without phase restriction errors

### Step 3: Test Add Issue Functionality in IDLE Phase
Select "+" option from menu
Follow prompts to add an available issue from Kanban

### Expected Result:
- Kanban issues list displays
- Can select and add issue successfully
- Confirmation message shows
- Active issues list updates

### Step 4: Test Remove Issue Functionality (if multiple issues exist)
Select "-" option from menu
Follow prompts to remove an issue (keeping at least 1)

### Expected Result:
- Current active issues list displays
- Can select and remove issue successfully
- Confirmation message shows
- Remaining issues list updates

### Step 5: Test in Other Phases
Repeat Steps 2-4 after transitioning to:
- SELECTING phase (select issue first)
- CODING phase
- REVIEWING phase (after creating PR)
- PREFLIGHT phase
- PR_PENDING phase

### Expected Result:
Add/remove options remain visible and functional in all phases

## 2. Testing VCS_CLI Configuration Support

### Step 1: Test with GitHub CLI (default)
Ensure VCS_CLI is not set or set to "gh"
Run roadmap update action (option U)
Verify it uses gh commands for issue verification

### Expected Result:
Roadmap updates successfully using GitHub CLI

### Step 2: Test with GitLab CLI
Set environment variable: `export VCS_CLI=glab`
Run roadmap update action
Verify it uses glab commands

### Expected Result:
Roadmap updates successfully using GitLab CLI
Error messages reference "glab" instead of "gh"

## 3. Testing GitLab Repo Detection

### Step 1: Verify Repo Detection
In a GitLab-based project worktree
Run any Luma action that requires repo detection
Check that repo name shows correct format (e.g., oatricedev/projectname)

### Expected Result:
Repo detected as "oatricedev/projectname" instead of malformed names

### Step 2: Test CLI Commands with Correct Repo
Run issue-related actions
Verify --repo parameter uses correct repo name in CLI calls

### Expected Result:
CLI commands succeed with proper repo parameter

## 4. Integration Testing

### Step 1: Full Workflow Test
Run complete workflow from IDLE to PR creation
Use add/remove options at different phases
Ensure no phase restriction errors

### Expected Result:
Workflow completes successfully with add/remove working in all phases

### Step 2: Error Handling Test
Try to remove issues when only 1 exists
Try to add issues when none available
Try invalid selections

### Expected Result:
Appropriate error messages displayed, no crashes

## 5. Testing GitLab CLI Field Compatibility (Issue #97)

### Step 1: Test with GitLab CLI
Set environment variable: `export VCS_CLI=glab`
Ensure repository is a GitLab repo (contains "gitlab" in repo name)
Run metrics sync action (option 4 in Issue Metrics menu)

### Expected Result:
- No field mismatch errors
- GitLab CLI command uses correct fields: `number,createdAt,closedAt,state`
- Status mapping works correctly (opened→🟡 In Progress, closed→✅ Complete)

### Step 2: Test with GitHub CLI (fallback)
Set environment variable: `export VCS_CLI=gh` or unset it
Run same metrics sync action

### Expected Result:
- GitHub CLI command uses full fields: `number,createdAt,closedAt,projectItems,stateReason`
- ProjectItems and stateReason processing works correctly

### Step 3: Mixed Environment Test
Test both CLI tools in same session to ensure proper switching

### Expected Result:
- Platform detection works correctly based on repo name and CLI tool
- No cross-contamination between GitHub and GitLab field handling

## Success Criteria

- ✅ Add/remove options visible in all 6 workflow phases
- ✅ Add/remove functionality works in all phases
- ✅ VCS_CLI configuration respected (gh/glab)
- ✅ GitLab repo detection works correctly
- ✅ GitLab CLI field compatibility works (Issue #97)
- ✅ No regressions in existing functionality
- ✅ All tests pass (pytest)
- ✅ Documentation updated correctly