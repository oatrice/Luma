# Manual Verification Guide: Issue #90 - CLI Fix Invalid Selection

## Prerequisites

-  Luma environment  (Python 3.9+, GitHub CLI authenticated)
-  GitHub project   with Kanban and issues in "Ready" or "In Progress" status (at least 3-4 issues)
-  CODING phase  (after selecting an issue)
-  Real CLI or headless mode  for testing

---

## Verification Scenarios

### Scenario 1: Comma-separated Multiple Issues (Happy Path)

**Addresses:** Core issue #90 - Fix "Invalid selection" when typing comma-separated like "1,2,3"

**Steps:**
1. Run Luma CLI and select project
2. Select an issue to enter CODING phase (if not already)
3. Select menu "Add Issue to Current Work Session"
4. When prompted "Select issue(s) to add:", type "1,2,3"
5. Observe output

**Expected Result:**
-  Success messages: " Added #X: Title" for each issue
-  "Active issues: #X, #Y, #Z" showing 3 issues
-  No error messages
-  State updated correctly (check with `luma state` or `.luma_state.json`)

---

### Scenario 2: Space-separated Multiple Issues (Extended Support)

**Steps:**
1. Same as Scenario 1, but type "1 2 3" instead of "1,2,3"

**Expected Result:**
-  Same as Scenario 1 - issues added successfully with proper messages

---

### Scenario 3: Remove Multiple Issues (New Feature)

**Steps:**
1. Ensure you have 4+ active issues in CODING phase
2. Select menu "Remove Issue from Current Work Session"
3. When prompted "Select issue to remove:", type "3,4"
4. Observe output

**Expected Result:**
-  "Removed #X: Title" for each removed issue
-  "Remaining: #X, #Y" showing remaining issues
-  At least 1 issue remains active

---

### Scenario 4: Invalid Index Handling

**Steps:**
1. From Add Issue menu, type "1,99" (assuming only 3-4 issues available)

**Expected Result:**
-  " Invalid index: 99" error message
-  Valid issue (1) still added successfully
-  Active issues increased by 1

---

### Scenario 5: Duplicate Prevention

**Steps:**
1. Add issue 1 with "1"
2. Select "Add Issue" again and type "1,2"

**Expected Result:**
-  " #61 already active, skipping" warning for issue 1
-  Only issue 2 added
-  Active issues total: 2 (1 existing + 1 new)

---

### Scenario 6: Single Issue Backward Compatibility

**Steps:**
1. From Add Issue menu, type "1" (single digit)

**Expected Result:**
-  Issue 1 added successfully
-  " Added #61: Title1" success message
-  Active issues updated correctly

---

## Conclusion

If all scenarios pass, implementation fully addresses Issue #90 and is ready for production.
