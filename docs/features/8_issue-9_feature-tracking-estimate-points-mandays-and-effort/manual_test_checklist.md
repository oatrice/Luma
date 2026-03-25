# 🧪 Manual Test Checklist: Issue Metrics Tracking V1

Use this checklist to manually verify the first implementation phase of issue metrics tracking in Luma.

## Scope

This checklist verifies:
- Per-project local storage in `.luma_metrics.json`
- GitHub Issue only flow
- Project-first, then issue selection
- Issue metrics list view
- Create, edit, and clear field behavior
- Persistence across restarts
- Validation for numeric, datetime, and effort fields
- Project isolation

This checklist does not cover:
- Cross-project aggregation
- Export to JSON or CSV
- Velocity or advanced metrics
- Syncing metrics back to GitHub Project custom fields

---

## Suggested Automated Regression

Run these first to catch obvious regressions before manual testing:

```bash
cd /Users/oatrice/Software-projects/Luma
python3 -m pytest tests/test_issue_metrics.py tests/test_action_issue_metrics.py tests/test_action_status_workflow.py tests/test_state_manager.py tests/test_main_global_config.py -q
```

- [ ] All targeted tests passed

---

## Preconditions

- [ ] `gh` CLI is installed and authenticated
- [ ] `python3 main.py` starts normally in the Luma repo
- [ ] At least one configured project has visible GitHub issues on its project board
- [ ] You know at least two projects to test isolation behavior

---

## Test 1: Open Metrics Menu

**Goal**: Verify the new menu entry and entry flow.

- [ ] Run:
  ```bash
  cd /Users/oatrice/Software-projects/Luma
  python3 main.py
  ```
- [ ] Verify the main menu shows `M` / `Track Issue Metrics`
- [ ] Select `M`
- [ ] Verify Luma asks to choose a project first
- [ ] Verify pressing `Enter` chooses the current project
- [ ] Verify selecting `0` returns safely without errors

---

## Test 2: Create Metrics for a GitHub Issue

**Goal**: Verify a new metrics record can be created for an issue.

- [ ] Enter the metrics menu
- [ ] Select a project
- [ ] Choose `2` = `Select GitHub issue to view/edit metrics`
- [ ] Verify the issue picker shows issues from the selected project's repo
- [ ] Select one issue
- [ ] Enter values such as:
  - `Estimate Points` = `8`
  - `Estimated Mandays` = `3.5`
  - `Actual Mandays` = `1.25`
  - `Due Date/Time` = `2026-03-20 14:30`
  - `Actual Completion Date/Time` = `2026-03-21 18:00`
  - `Effort Level` = `High`
  - `Notes` = `Ready to ship`
- [ ] Verify Luma prints `Issue metrics saved.`

---

## Test 3: Verify `.luma_metrics.json` Is Written

**Goal**: Verify storage happens in a separate local JSON file.

- [ ] Open the selected project's root directory
- [ ] Verify a file named `.luma_metrics.json` exists
- [ ] Verify the saved issue appears in that file
- [ ] Verify the record includes:
  - `estimate_points`
  - `estimated_mandays`
  - `actual_mandays`
  - `due_date`
  - `actual_completion_date`
  - `effort_level`
  - `notes`
  - `updated_at`
- [ ] Verify date/time values are stored in ISO format

---

## Test 4: List Tracked Issues

**Goal**: Verify the summary list shows tracked issues for the chosen project.

- [ ] Re-enter the metrics menu for the same project
- [ ] Choose `1` = `List tracked issues`
- [ ] Verify the tracked issue appears in the list
- [ ] Verify the list shows short columns for:
  - Issue number
  - Title
  - Estimate points
  - Estimated mandays
  - Actual mandays
  - Due date/time
  - Effort level
- [ ] Verify the total tracked count is shown

---

## Test 5: Edit an Existing Record

**Goal**: Verify tracked issue records can be edited safely.

- [ ] In the metrics menu, choose `3` = `Open tracked issue`
- [ ] Select the issue created earlier
- [ ] Change only one or two values, for example:
  - `Actual Mandays` from `1.25` to `2`
  - `Notes` to a new value
- [ ] Press `Enter` on fields that should remain unchanged
- [ ] Verify Luma prints `Issue metrics saved.`
- [ ] Re-open the same tracked issue
- [ ] Verify changed fields were updated
- [ ] Verify untouched fields remained unchanged

---

## Test 6: Clear Existing Values

**Goal**: Verify fields can be cleared explicitly.

- [ ] Open an existing tracked issue
- [ ] Enter `-` for one or more fields, such as:
  - `Actual Completion Date/Time`
  - `Notes`
- [ ] Save the record
- [ ] Re-open the issue
- [ ] Verify the cleared fields are now empty / unset

---

## Test 7: Validation for Numeric Fields

**Goal**: Verify invalid numeric input is rejected and `0` is allowed.

- [ ] Open a metrics form
- [ ] Try `Estimate Points = abc`
- [ ] Verify Luma rejects the input with an error
- [ ] Try `Estimated Mandays = -1`
- [ ] Verify Luma rejects the input with an error
- [ ] Try `Actual Mandays = -5`
- [ ] Verify Luma rejects the input with an error
- [ ] Try `Estimate Points = 0`
- [ ] Verify it is accepted
- [ ] Try `Estimated Mandays = 0`
- [ ] Verify it is accepted
- [ ] Try `Actual Mandays = 0`
- [ ] Verify it is accepted

---

## Test 8: Validation for Datetime Fields

**Goal**: Verify date-only input is rejected and datetime input is accepted.

- [ ] Open a metrics form
- [ ] Try `Due Date/Time = 2026-03-20`
- [ ] Verify Luma rejects it
- [ ] Try `Due Date/Time = 2026-03-20 14:30`
- [ ] Verify it is accepted
- [ ] Try `Actual Completion Date/Time = 2026-03-21`
- [ ] Verify Luma rejects it
- [ ] Try `Actual Completion Date/Time = 2026-03-21 18:00`
- [ ] Verify it is accepted

---

## Test 9: Validation for Effort Level

**Goal**: Verify effort level is limited to the supported enum.

- [ ] Open a metrics form
- [ ] Try `Effort Level = Very High`
- [ ] Verify Luma rejects it
- [ ] Try `Effort Level = High`
- [ ] Verify it is accepted
- [ ] Try `Effort Level = Medium`
- [ ] Verify it is accepted
- [ ] Try `Effort Level = Low`
- [ ] Verify it is accepted

---

## Test 10: Persistence Across Restart

**Goal**: Verify metrics survive closing and reopening Luma.

- [ ] Save at least one metrics record
- [ ] Exit Luma fully
- [ ] Run `python3 main.py` again
- [ ] Open the metrics menu
- [ ] Select the same project
- [ ] Choose `1` or `3`
- [ ] Verify the tracked issue and its values still exist

---

## Test 11: Project Isolation

**Goal**: Verify each project uses its own `.luma_metrics.json`.

- [ ] Track at least one issue in project A
- [ ] Track at least one issue in project B
- [ ] In project A, list tracked issues
- [ ] Verify only project A records are shown
- [ ] In project B, list tracked issues
- [ ] Verify only project B records are shown
- [ ] Verify each project root contains its own `.luma_metrics.json`

---

## Test 12: Repo Filtering in Issue Picker

**Goal**: Verify the issue picker stays within the selected project's repo.

- [ ] Choose a project whose GitHub board contains multiple repos or shared board items
- [ ] Open `Select GitHub issue to view/edit metrics`
- [ ] Verify the list excludes issues from other repos
- [ ] Verify selected issue belongs to the chosen project repo

---

## Test 13: ROADMAP Is Reference Only

**Goal**: Verify metrics are not auto-imported from roadmap content.

- [ ] Open or update `ROADMAP.md` in a tested project with estimate-like notes
- [ ] Start Luma and open the metrics tracker
- [ ] Select the same issue
- [ ] Verify metrics fields are empty unless they were explicitly saved into `.luma_metrics.json`
- [ ] Verify roadmap notes do not auto-populate fields

---

## Exit Criteria

- [ ] Metrics menu is reachable and usable
- [ ] New record creation works
- [ ] Existing record editing works
- [ ] Clearing values works
- [ ] Validation blocks invalid inputs
- [ ] `0` is accepted for numeric fields
- [ ] Datetime fields require date and time
- [ ] `.luma_metrics.json` is written correctly
- [ ] Data survives restart
- [ ] Tracked issues list works
- [ ] Project isolation works
- [ ] Issue picker respects selected project repo
- [ ] ROADMAP remains reference only

If all items above pass, V1 manual verification is complete.
