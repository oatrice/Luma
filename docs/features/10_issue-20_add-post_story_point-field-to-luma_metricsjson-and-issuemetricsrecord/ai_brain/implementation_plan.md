# Implementation Plan: Gemini CLI Restoration & Metrics Optimization

We have successfully restored the `gemini` CLI via Homebrew. This plan outlines the final steps to ensure Luma uses the restored binary correctly, optimizes the fallback chain, and polishes the metrics reporting as requested.

## User Review Required

> [!IMPORTANT]
> **Gemini CLI Path**: I will point Luma to use `/opt/homebrew/bin/gemini` explicitly in the configuration to ensure it remains stable even if the `HOME` environment variable is overridden during account rotation.

## Proposed Changes

### LLM Integration
#### [MODIFY] [llm.py](file:///Users/oatrice/Software-projects/Luma/luma_core/llm.py)
- Update `GeminiCLIModel` to use the absolute path `/opt/homebrew/bin/gemini` for subprocess calls.
- Ensure the `run_manager` fix (already implemented) is stable.
- Rename internal reporting of CLI usage from 'gemini' to 'gemini-cli' for clarity.

---
### Metrics Reporting
#### [MODIFY] [metrics_summarizer.py](file:///Users/oatrice/Software-projects/Luma/luma_core/metrics_summarizer.py)
- Verify `_format_duration` correctly handles hours (e.g., `103m` -> `1h 43m`).
- Ensure the breakdown truncation (Top 10 sub-actions, Top 5 actions) is strictly enforced to prevent message cutting.

---
### Configuration
#### [MODIFY] [.env](file:///Users/oatrice/Software-projects/Luma/.env)
- Update placeholders with guidance for the user to add real API keys for OpenAI/OpenRouter to complete the fallback chain.

## Verification Plan

### Automated Tests
- Run `tests/test_llm_run_manager.py` to ensure the core fix remains intact.
- Run `tests/test_metrics_summarizer.py` (or create a new one) to verify duration formatting for values > 60 minutes.

### Manual Verification
- Run `gemini --version` via a small script using `subprocess.Popen` in the Luma environment to ensure connectivity.
- Trigger a mock summary generation to see the "Workflow Summary" layout.
