# Walkthrough: Reuse Planning Repos in Update Docs

## Overview
Updated `action_update_docs` to check whether `state.context.get("target_planning_repos")` contains any selected repositories from the **Planning Phase**. If so, it reuses those repositories directly, bypassing the interactive prompt.

## Changes Made
- Added a check in `luma_core/actions.py`: `target_planning_repos = state.context.get("target_planning_repos", [])`.
- If `target_planning_repos` exists, `target_repos` is assigned to it, and a success message is printed: `✅ Using selected repositories from Planning Phase`.
- If not, it falls back to the original behavior (looking up siblings and prompting appropriately).
- Added test coverage in `tests/test_action_update_docs.py` with cases for both when the context has the selected repos and when it doesn't.

## Automated Tests
- Created `test_action_update_docs_uses_planning_repos_from_context` to verify that `update_multi_repo_docs` is called with the selected repos without prompting.
- Created `test_action_update_docs_fallback_when_no_context` to verify the fallback logic works seamlessly when the key isn't present.
- All tests are green.

## Manual Verification
- You can test this functionally by starting an issue that triggers the **Planning phase** multi-repo selector, and noticing that later in the docs update phase, it no longer asks "Select projects to update docs".
