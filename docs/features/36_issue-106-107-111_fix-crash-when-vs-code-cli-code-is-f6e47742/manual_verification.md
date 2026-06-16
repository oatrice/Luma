### Manual Verification Guide

**Step 1: Inspect the newly generated feature artifacts**
- Open your terminal and navigate to the project directory: `cd /Users/oatrice/Software\ Project/Luma`
- Check that the new feature folder exists: `ls -l "docs/features/36_issue-106-107-111_fix-crash-when-vs-code-cli-code-is-f6e47742"`
- Verify that three files are present in this folder: `task.md`, `walkthrough.md`, and `implementation_plan.md`.

**Step 2: Verify the content of the artifacts**
- Open `docs/features/36_issue-106-107-111_fix-crash-when-vs-code-cli-code-is-f6e47742/implementation_plan.md` in your text editor.
- Confirm that it details the proposed changes for Luma Core's `workflow_actions.py` and `publisher.py` to support the Force Export Prompt feature and resolve the MR check bug.
- Open `task.md` and check that all task checkboxes (`[ ]`) are correctly tracking the steps outlined.
- Open `walkthrough.md` and verify that the summary accurately reflects the modifications described.

**Expected Result:**
All three files should exist and their contents should correctly describe the implementation plan, tasks, and walkthrough for issues 106, 107, and 111 as requested.
