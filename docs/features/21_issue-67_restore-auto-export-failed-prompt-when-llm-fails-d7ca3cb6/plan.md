# Implementation Plan: Restore: Auto-export failed prompt when LLM fails with human-readable timestamp

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `luma_core/gemini_cli.py`: Will contain the logic for capturing prompts, generating timestamps, and initiating the export on LLM failure.
    - `luma_core/llm.py`: Will be updated to call the export logic during LLM failure handling after retries.
    - `luma_core/config.py`: Will be updated to reflect the default behavior of `LUMA_EXPORT_PROMPTS` (though the runtime decision to force `true` on error will be in `llm.py`).
    - `luma_core/tools.py`: May be used for a helper function to manage directory creation or file writing if a new utility is warranted.
- **New Components**:
    - A new directory `docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/` will be created if it does not exist, to store the exported prompts.
    - A new test file `tests/test_llm_prompt_export.py` to cover the new functionality.
- **Dependencies**: No new external dependencies. Relies on `datetime` for timestamp generation and `os` for file system operations.

### Data Model Changes
No new data structures or database schema changes are required.

---

## 2. Step-by-Step Implementation

### Step 1: Identify LLM Failure Point and Implement Prompt Export Utility
- **Docs**: Analyze `luma_core/llm.py` (specifically methods related to `GeminiCLIModel` and retry logic) to locate the exact point where an LLM call is considered a definitive failure after exhausting all retries.
- **Code**:
    1.  In `luma_core/llm.py` (or `luma_core/gemini_cli.py`), identify the `_generate` method or the primary LLM call wrapper where exceptions are caught and retries are managed.
    2.  Create a new private helper function, e.g., `_export_failed_prompt_to_file(prompt: str, export_path: str)` within `luma_core/llm.py` or `luma_core/gemini_cli.py`.
    3.  This function will:
        *   Generate a human-readable timestamp in `YYYYMMDD_HHMMSS` format.
        *   Construct the target file path: `docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/luma_failed_prompt_{timestamp}.md`.
        *   Ensure the directory `docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/` exists using `os.makedirs(..., exist_ok=True)`.
        *   Write the `prompt` content to the generated file.
        *   Print a user-facing message indicating the export path.
- **Tests**: Create `tests/test_llm_prompt_export.py`.
    - Add a unit test for `_export_failed_prompt_to_file` to verify:
        - Correct timestamp format (`YYYYMMDD_HHMMSS`).
        - Correct file path generation.
        - Directory creation (`os.makedirs` mock).
        - File content is correct.
        - User message is displayed.

### Step 2: Integrate Export Logic into LLM Failure Handling and Implement Configuration Default
- **Docs**: Detail how the export utility will be invoked and how `LUMA_EXPORT_PROMPTS` will influence this.
- **Code**:
    1.  In `luma_core/llm.py` (or the relevant LLM wrapper), within the `except` block that catches final LLM failures after all retries are exhausted:
        *   Retrieve the original prompt that caused the failure.
        *   Check the `LUMA_EXPORT_PROMPTS` configuration value from `luma_core/config.py`.
        *   If `LUMA_EXPORT_PROMPTS` is not explicitly `false` (i.e., it's `true` or undefined), call `_export_failed_prompt_to_file` with the captured prompt.
        *   The logic here will implicitly set `LUMA_EXPORT_PROMPTS` to `true` for this failure instance if it wasn't explicitly `false`.
    2.  Update `luma_core/config.py` to ensure `LUMA_EXPORT_PROMPTS` exists as a configurable option, potentially with a `None` or dynamic default that indicates it can be overridden by runtime failure logic.
- **Tests**: Expand `tests/test_llm_prompt_export.py`.
    - Add integration tests (or mock `llm.py` behavior) to verify:
        - Prompt is exported when `LUMA_EXPORT_PROMPTS` is `true`.
        - Prompt is exported when `LUMA_EXPORT_PROMPTS` is not explicitly `false` during an LLM error.
        - Prompt is NOT exported when `LUMA_EXPORT_PROMPTS` is `false`.
        - The correct user message is displayed only when export occurs.
    - Mock the LLM `_generate` method to simulate failure scenarios after retries.

### Step 3: Verify `.gitignore` Compatibility
- **Docs**: Confirm the `.gitignore` entry.
- **Code**: No code changes needed if `luma_failed_prompt_*.md` is already in `.gitignore`. A quick check will confirm this.
- **Tests**: Add a simple assertion (if possible, or document as manual verification) in `tests/test_llm_prompt_export.py` to confirm the `.gitignore` pattern.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [x] Unit Tests: `tests/test_llm_prompt_export.py` (for `_export_failed_prompt_to_file` function).
- [x] Integration Tests:
    - Simulate LLM failures after retries.
    - Verify file creation, content, and path when `LUMA_EXPORT_PROMPTS` is true or defaulted due to error.
    - Verify no file creation when `LUMA_EXPORT_PROMPTS` is false.
    - Verify correct user messages are displayed.

### Manual Verification
- [ ] Trigger an LLM failure intentionally (e.g., by providing an invalid API key or forcing a timeout).
- [ ] Observe that a `.md` file with the failed prompt is created in `docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/`.
- [ ] Verify the filename contains a human-readable timestamp in the `YYYYMMDD_HHMMSS` format.
- [ ] Check the content of the exported `.md` file to ensure it matches the problematic prompt.
- [ ] Verify that a user-facing message is displayed in the terminal indicating the export.
- [ ] Set `LUMA_EXPORT_PROMPTS` to `false` in the configuration (e.g., `.env`) and repeat the LLM failure test, ensuring no prompt file is created and no export message is displayed.
- [ ] Confirm that `luma_failed_prompt_*.md` files are ignored by Git (using `git status` after export).