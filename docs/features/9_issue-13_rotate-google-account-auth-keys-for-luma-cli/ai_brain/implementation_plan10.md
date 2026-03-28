# Implementation Plan: Fix Gemini CLI Profile Isolation

Modify `GeminiCLIModel` to use the `HOME` environment variable for OAuth profile isolation, as the current version of the Gemini CLI (v0.35.3) does not respect `GEMINI_CONFIG_HOME`.

## Proposed Changes

### [luma_core](file:///Users/oatrice/Software-projects/Luma/luma_core)

#### [MODIFY] [llm.py](file:///Users/oatrice/Software-projects/Luma/luma_core/llm.py)
- In `GeminiCLIModel._generate`, change `subprocess_env["GEMINI_CONFIG_HOME"]` to `subprocess_env["HOME"]`.
- This will cause the `gemini` CLI to look for its configuration at `$HOME/.gemini/oauth_creds.json`, which will resolve to the profile-specific path (e.g., `~/.config/gemini/personal/.gemini/oauth_creds.json`).

## Verification Plan

### Automated Tests
- Run existing tests to ensure no regressions:
  `pytest tests/test_llm_gemini_cli.py`
- I will add a new test case to specifically verify that `HOME` is being correctly set when an OAuth profile is used.

### Manual Verification
- The user has already verified that setting `HOME` creates the expected `Library/Application Support/Antigravity` structure (and presumably the `.gemini` folder as well).
- I will ask the user to run a simple `luma` command or `gemini` command with the new logic to confirm one last time.
