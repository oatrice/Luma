# Handoff Notes: Refactor Publisher Agent & AI PR Body

**Date:** 2026-01-19
**Status:** In Progress
**Context:** resolving `ImportError` in Publisher Agent (Done) -> Enhancing PR creation with AI (Next).

## ✅ What's Done
1.  **Refactored Publisher Agent:**
    - Ported `github_fetcher.py` logic to `luma_core/github_client.py`.
    - Updated `publisher.py` to use the new client.
    - **Fixed `TARGET_DIR` issue:** `publisher_agent` now correctly receives `target_dir` from `main.py` state, instead of using a hardcoded global value.
    - Updated `config.py` to remove the dangerous hardcoded `TARGET_DIR`.
    - Verified functionality: User successfully created a PR (despite a 422 error log, user confirmed success).

## 🚧 What's Next (Immediate Action)
**Goal:** Modify `publisher_agent` to use AI for generating PR descriptions instead of static text.

**Refer to Implementation Plan:** `docs/20260119-224317-ai-pr-body-gen/implementation.md`

**Steps:**
1.  **Modify `luma_core/agents/publisher.py`**:
    - Capture git diff/commit context.
    - Construct a prompt for the LLM.
    - **Crucial:** Save the draft prompt to a text file (e.g., `draft_pr_prompt.txt`) *before* calling the LLM (as requested by user).
    - Call `get_llm()` to generate the body.
    - Use the generated body in `create_pull_request` / `update_pull_request`.

## 📂 Relevant Files
- `luma_core/agents/publisher.py`: Main logic to be updated.
- `luma_core/github_client.py`: GitHub interaction helper (already working).
- `.github/pull_request_template.md`: Template to be read by the agent (if exists in target repo).
