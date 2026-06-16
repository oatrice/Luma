### Manual Verification Guide

**Test 1: Verify Worktree Context Bug (Issue #110)**
- Step 1: Open your terminal and change directory to the base Luma repository (not a worktree).
- Step 2: Start Luma and select a project that is configured as a Git worktree.
- Step 3: Check the targeted directory in the Luma interface or logs.
- Expected Result: Luma should operate within the selected worktree path instead of falling back to the base repository path.

**Test 2: Verify Publisher Agent MR Repo Bug (Issue #109)**
- Step 1: Using Luma, select a GitLab project (e.g., FonMaYang) and make a dummy code change.
- Step 2: Ask the Publisher Agent to create a Merge Request for these changes.
- Expected Result: The `glab mr create` command successfully creates the Merge Request on the target project's repository, rather than incorrectly creating it on the Luma repository.

**Test 3: Verify Notifications URL Update**
- Step 1: In the terminal, run the test suite for the notifier using `pytest tests/test_notifier.py`.
- Step 2: Ensure that your `AKASA_API_URL` environment variable is either unset or points to the new production URL.
- Step 3: Complete a task using Luma to trigger the `notify_task_complete` function.
- Expected Result: The test suite should pass, and the task completion notification should be successfully sent to the `https://akasa-backend-6a8v.onrender.com` backend.
