## Manual Verification Guide

### Scenario 1: Removal of `code_review_prompt.txt` and Correct Worktree Path Resolution

**Goal:** Verify that `code_review_prompt.txt` is no longer created and that `code_review.md` is generated in the correct Git worktree directory.

**Assumptions:**
*   You have `luma` CLI installed and configured.
*   You are familiar with basic Git commands, including creating worktrees.

**Steps:**

1.  **Set up a test repository:**
    *   Create a new directory for your test repository:
        ```bash
        mkdir luma-test-repo
        cd luma-test-repo
        git init -b main
        echo "Initial content" > file1.txt
        git add .
        git commit -m "Initial commit"
        ```
    *   Create a Git worktree named `feat-test`:
        ```bash
        git worktree add ../luma-test-repo-feat-test feat-test
        ```
    *   Navigate into the newly created worktree directory:
        ```bash
        cd ../luma-test-repo-feat-test
        ```
    *   Make some changes in the worktree to trigger a code review. For example, add a new file:
        ```bash
        echo "def my_func():
    pass" > new_feature.py
        git add new_feature.py
        git commit -m "feat: Add new feature"
        ```

2.  **Execute the Luma Code Review command:**
    *   Run the Luma command that triggers a code review (e.g., for a PR summary). *Note: The exact command might vary based on your Luma configuration. If `luma create pr-summary` is not the correct command, use the one that generates `code_review.md`.*
        ```bash
        luma create pr-summary --repo-path .
        ```
    *   Follow any interactive prompts from Luma.

3.  **Verify absence of `code_review_prompt.txt`:**
    *   Check if the file `code_review_prompt.txt` exists in the current worktree directory (`luma-test-repo-feat-test/`):
        ```bash
        ls code_review_prompt.txt
        ```

    *   **Expected Result:** The `ls` command should return an error indicating that `code_review_prompt.txt` does not exist.

4.  **Verify `code_review.md` location:**
    *   Check for the presence of `code_review.md` in the root of the current worktree directory (`luma-test-repo-feat-test/`):
        ```bash
        ls code_review.md
        ```
    *   **Expected Result:** The `ls` command should successfully find and list `code_review.md` within `luma-test-repo-feat-test/`. The content of `code_review.md` should reflect the review of `new_feature.py`.

### Scenario 2: Non-Worktree Repository Behavior (No Regression)

**Goal:** Verify that Luma still functions correctly when run in a standard (non-worktree) Git repository.

**Steps:**

1.  **Navigate back to the main repository:**
    ```bash
    cd ../luma-test-repo
    ```
    *   Ensure you are on the `main` branch or another non-worktree branch.

2.  **Make some changes:**
    ```bash
    echo "Another line" >> file1.txt
    git add .
    git commit -m "Update file1"
    ```

3.  **Execute the Luma Code Review command:**
    ```bash
    luma create pr-summary --repo-path .
    ```

4.  **Verify `code_review.md` location:**
    *   Check for the presence of `code_review.md` in the root of this main repository (`luma-test-repo/`):
        ```bash
        ls code_review.md
        ```

    *   **Expected Result:** The `ls` command should successfully find and list `code_review.md` within `luma-test-repo/`. The content should reflect the review of `file1.txt`.

5.  **Clean up (Optional):**
    ```bash
    rm -rf ../luma-test-repo ../luma-test-repo-feat-test
    ```