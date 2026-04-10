# SBE (Specification by Example) Template

> 📅 Created: 2026-04-09
> 🔗 Issue: https://github.com/oatrice/Luma/issues/67

---

## Feature: Restore Auto-export of Failed LLM Prompts

Automatically export the LLM prompt to a markdown file when the Gemini CLI fails or times out after all retries are exhausted. This helps developers copy-paste the failed prompt into an external AI interface to continue the task. The exported file uses a human-readable timestamp and is stored within the specific feature's directory.

### Scenario: Export Prompt on LLM Failure (Happy Path)

**Given** a feature directory exists for the current task
**And** the LLM request fails after the maximum number of retries
**When** the system triggers the auto-export logic
**Then** a markdown file is created with the human-readable timestamp `YYYYMMDD_HHMMSS`
**And** the console displays a success message with the full path to the exported prompt

#### Examples

| Issue Number | Issue ID | Current Time | Expected File Path |
|--------------|----------|--------------|-------------------|
| 67 | restore-auto-export | 2026-04-09 21:05:00 | docs/features/67_issue-restore-auto-export/ai_brain/luma_failed_prompt_20260409_210500.md |
| 15 | fix-timeout | 2026-04-09 09:30:15 | docs/features/15_issue-fix-timeout/ai_brain/luma_failed_prompt_20260409_093015.md |
| 42 | add-feature-x | 2026-04-10 14:00:59 | docs/features/42_issue-add-feature-x/ai_brain/luma_failed_prompt_20260410_140059.md |

---

### Scenario: Automatic Directory Creation (Edge Case)

**Given** a feature directory exists but the `ai_brain` subdirectory is missing
**When** an LLM failure occurs and an export is required
**Then** the system should automatically create the `ai_brain` directory
**And** successfully save the `luma_failed_prompt_{timestamp}.md` file inside it

#### Examples

| Subdirectory State | Action | Expected Result |
|--------------------|--------|-----------------|
| Missing `ai_brain` | Export triggered | Directory created, file saved successfully |
| Existing `ai_brain`| Export triggered | File saved successfully in existing directory |
| Read-only parent   | Export triggered | System logs error but does not crash |

---

### Scenario: Default Configuration and Overrides (Boundary Conditions)

**Given** the configuration for `LUMA_EXPORT_PROMPTS` is set or omitted
**When** an LLM error occurs (Timeout, Connection Error, or Model Error)
**Then** the system decides whether to export based on the priority: Environment Variable > Default (True)

#### Examples

| Environment Variable Value | LLM Error Type | Export Performed? | Reason |
|----------------------------|----------------|-------------------|--------|
| (Not Set) | Timeout | Yes | Default is `true` for robustness |
| "true" | Connection Error | Yes | Explicitly enabled |
| "false" | Model Error | No | Explicitly disabled by user |
| "true" | Success (No Error) | No | No failure occurred |

---

## Notes

- The timestamp format must be strictly `YYYYMMDD_HHMMSS` to ensure file system compatibility and human readability.
- The `ai_brain` directory is the standard location for LLM-related debugging assets within a feature folder.
- The `.gitignore` file already contains patterns to ignore these failed prompt files, so they won't be accidentally committed to the repository.
- Ensure that the console message starts with the ❌ emoji as per the requirements.