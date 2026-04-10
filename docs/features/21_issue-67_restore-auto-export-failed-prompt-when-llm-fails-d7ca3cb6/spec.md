# Specification: Restore: Auto-export failed prompt when LLM fails with human-readable timestamp

> **Status**: Draft
> **Owner**: AI Architect
> **Dates**: Created: 2026-04-09 | Last Updated: 2026-04-09

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
The feature for automatically exporting failed LLM prompts to `.md` files was removed in commit `1aa97f2` as part of refactoring LLM robustness. This removal makes it significantly harder to debug and analyze the root causes of LLM failures or timeouts.

### Goal
Restore the functionality to automatically export failed LLM prompts to `.md` files. When the Gemini CLI model fails or times out after all retries are exhausted, the system should save the prompt used for the generation. This exported prompt should include a human-readable timestamp in the `YYYYMMDD_HHMMSS` format and be saved in a structured directory path (`docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/`). Furthermore, the `LUMA_EXPORT_PROMPTS` configuration setting should default to `true` when LLM errors are encountered, ensuring this diagnostic export is enabled by default during failure scenarios.

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **Developer**, I want to have failed LLM prompts automatically exported to `.md` files with human-readable timestamps, so that I can easily analyze and debug LLM failures without manual intervention.

### Functional Requirements
- [x] When the `GeminiCLIModel._generate()` method fails after exhausting all configured retries, capture the prompt that was sent to the LLM.
- [x] Save the captured prompt content to a `.md` file.
- [x] Generate a human-readable timestamp in `YYYYMMDD_HHMMSS` format for use in the filename.
- [x] Construct the save path for the exported prompt file as: `docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/luma_failed_prompt_{timestamp}.md`.
- [x] When an LLM error occurs and the `LUMA_EXPORT_PROMPTS` setting is not explicitly configured to `false`, automatically enable prompt export (effectively setting it to `true` for that instance).
- [x] Update `luma_core/config.py` to ensure the default behavior for `LUMA_EXPORT_PROMPTS` is correctly handled when LLM issues are detected.
- [x] Display a user-facing message indicating that the prompt has been exported and providing the path to the saved file.
- [x] Verify that the generated filenames are compatible with the existing `.gitignore` entry for `luma_failed_prompt_*.md`.

### Non-Functional Requirements
- [ ] **Error Handling**: The export process itself should be robust and not fail if the LLM call fails.
- [ ] **Performance**: Prompt export should be a background operation and not significantly delay the error reporting or program exit.

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: LLM Failure with Auto-Export Enabled
**Given** the Gemini CLI model has exhausted all its retry attempts for a generation request.
**And** the `LUMA_EXPORT_PROMPTS` setting is either explicitly `true` or defaults to `true` due to the LLM error.
**When** the `GeminiCLIModel._generate()` method detects a final LLM failure.
**Then** the prompt sent to the LLM is saved to a `.md` file.
**And** the file is located at `docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/luma_failed_prompt_YYYYMMDD_HHMMSS.md` (where `YYYYMMDD_HHMMSS` is the current human-readable timestamp).
**And** a confirmation message is displayed to the user, e.g., "❌ Gemini CLI failed after retries. Exporting prompt to /path/to/ai_brain/luma_failed_prompt_YYYYMMDD_HHMMSS.md for external AI."

#### Examples
| LLM Failure State | `LUMA_EXPORT_PROMPTS` Config | Expected Action | Expected Output Message | Expected File Path Suffix |
|-------------------|----------------------------|-----------------|-------------------------|---------------------------|
| Failed (after retries) | `true`                     | Export prompt   | Confirmed export message | `luma_failed_prompt_YYYYMMDD_HHMMSS.md` |
| Failed (after retries) | `true` (defaulted due to error) | Export prompt | Confirmed export message | `luma_failed_prompt_YYYYMMDD_HHMMSS.md` |

### Scenario: LLM Failure with Auto-Export Disabled
**Given** the Gemini CLI model has exhausted all its retry attempts for a generation request.
**And** the `LUMA_EXPORT_PROMPTS` setting is explicitly `false`.
**When** the `GeminiCLIModel._generate()` method detects a final LLM failure.
**Then** the prompt sent to the LLM is NOT exported to a file.
**And** no export confirmation message is displayed to the user.

#### Examples
| LLM Failure State | `LUMA_EXPORT_PROMPTS` Config | Expected Action | Expected Output Message |
|-------------------|----------------------------|-----------------|-------------------------|
| Failed (after retries) | `false`                    | Do not export   | No export message       |

---

## 4. Constraints & Risks
*What should we watch out for?*
- **Constraint**: The restored feature must integrate seamlessly with the existing LLM robustness refactoring and avoid introducing regressions in other LLM functionalities.
- **Risk**: Incorrect parsing or generation of the human-readable timestamp could lead to invalid filenames, broken export paths, or failure to match the `.gitignore` pattern.
- **Risk**: The default behavior of setting `LUMA_EXPORT_PROMPTS=true` on LLM errors needs careful implementation to ensure it only triggers on genuine failures and not on less severe issues, to avoid unnecessary file generation.
- **Risk**: The target directory `docs/features/67_issue-67_restore-auto-export-failed-prompt/ai_brain/` may need to be created dynamically if it does not already exist.
- **Risk**: Ensure the commit that removed this functionality (`1aa97f2b9621567f7d0f1d3b2c384c21442c7c55`) is properly understood to avoid reintroducing bugs or conflicting logic.