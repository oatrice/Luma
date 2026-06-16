# Goal: Resolve Issues #106, #107, and #111

This plan covers the implementation details for resolving three related issues in Luma Core:
- **Issue #106 & #107**: Fix crash when the VS Code `code` CLI is missing during documentation generation/updates.
- **Issue #111**: Feature to force export prompt file for MR title/description without creating an MR, and fixing the bug where the `PR/MR already exists` check returns `None` for the MR URL.

## User Review Required
No major architectural changes.

## Proposed Changes

### 1. Fix Crash on Missing VS Code CLI (#106, #107)

#### [MODIFY] [luma_core/tools.py](file:///Users/oatrice/Software%20Project/Luma/luma_core/tools.py)
- Identify calls to `subprocess.run(["code", "--diff", ...])` during document preview.
- Wrap these calls in a `try-except FileNotFoundError` block to gracefully handle systems where the VS Code CLI is not installed or not in the `PATH`.
- Print a user-friendly warning message instead of terminating the process.

#### [NEW] [tests/test_tools_code_diff.py](file:///Users/oatrice/Software%20Project/Luma/tests/test_tools_code_diff.py)
- Create unit tests that mock `subprocess.run` to raise a `FileNotFoundError` and ensure that `luma_core.tools` catches the exception without crashing the application.

### 2. Force Export MR Prompt & Fix MR URL Bug (#111)

#### [MODIFY] [luma_core/actions/workflow_actions.py](file:///Users/oatrice/Software%20Project/Luma/luma_core/actions/workflow_actions.py)
- **Fix None URL bug:** In `action_create_pr`, when evaluating `pr_url`, add `.get('url')` as a fallback since the GitLab client returns `{"url": ...}` instead of `web_url`.
  ```python
  pr_url = existing.get('web_url') or existing.get('html_url') or existing.get('url')
  ```
- **Add Force Export Option:** In `action_guided_workflow`, update the input prompt:
  ```python
  choice = ui.safe_input("   Create PRs? [y] Yes (confirm each), [a] Yes to All (auto), [f] Force Export Prompt Only, [n] No: ").strip().lower()
  ```
- Handle the `f` choice by calling `action_create_pr(..., force_export_only=True)`.
- Update the `action_create_pr` signature to accept `force_export_only: bool = False`.
- In `action_create_pr`, skip the "Check for existing PR" step if `force_export_only` is true, ensuring it always reaches the publisher agent.
- Add `force_export_only` to the `pub_state` dictionary so the publisher agent knows to abort after exporting the prompt.

#### [MODIFY] [luma_core/agents/publisher.py](file:///Users/oatrice/Software%20Project/Luma/luma_core/agents/publisher.py)
- After the draft prompt is saved to `draft_pr_prompt.md`, check if `state.get("force_export_only")` is True.
- If True, print a message: `✅ Force Export Complete. Skipping PR creation.` and `return {"url": None}` immediately, bypassing the MR creation logic and API calls.

#### [NEW] [tests/test_pr_force_export.py](file:///Users/oatrice/Software%20Project/Luma/tests/test_pr_force_export.py)
- Create a unit test to verify that the `publisher_agent` properly respects the `force_export_only` flag and skips user interaction and API calls.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_tools_code_diff.py` to ensure the `code` CLI crash fix works.
- Run `pytest tests/test_pr_force_export.py` to ensure the force export mode bypasses API execution.
- Run the full test suite `pytest tests/` to ensure no regressions.

### Manual Verification
- Remove or rename the `code` binary temporarily, run Luma's workflow, and observe that it handles the diff gracefully instead of crashing.
- Run Luma via `python main.py` or equivalent, proceed to Step 6.
- Check if the prompt reads `Create PRs? [y] Yes (confirm each), [a] Yes to All (auto), [f] Force Export Prompt Only, [n] No: `.
- Select `f` and verify that `draft_pr_prompt.md` is generated and the execution successfully skips making an MR API call.
