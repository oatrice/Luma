# Walkthrough: Smart Fallback Strategy + Rate Limit Detection

## Changes Made
- **Error Classification**: Created `error_classifier.py` (`ErrorType` enum & `classify_error`) to identify `RATE_LIMIT`, `QUOTA_EXCEEDED`, and `TIMEOUT` string values.
- **Model Fallback Logic (`llm.py`)**: 
  - Integrated classification into `GeminiCLIModel` so that when a rate limit is hit, it raises an error directly instead of fruitlessly retrying.
  - Provided `FallbackModel` the ability to catch these errors and instantly push the fallback chain without `time.sleep` when classified as non-retryable.
  - Added specific hardcoded timeouts based on model speed (i.e. `gemini-3-flash-preview` -> 180s, `gemini-2.5-pro` -> 300s, etc.).
- **Usage Tracker Logging**: Modified `usage_tracker.py` to record `error_type` in `record_llm_event()`.
- **Model Tuning**: Edited `AVAILABLE_GEMINI_CLI_MODELS` in `config.py` to prioritize `gemini-2.5-flash` over `gemini-3-pro-preview` for overall stability.
- **Project ID Logic (`actions.py`)**: Changed `_add_new_project` IDs from Unix timestamps to an auto-incrementing integer sequence.
- **Tests Maintenance**: Fixed `LumaState` state assignment issue (`tests/test_ai_brain_sync.py`) and updated `builtins.input` mock limits in `tests/test_action_settings.py` triggered by an expanded config option.
- **Documentation Updates**: Updated version to `1.4.0` in `CHANGELOG.md` and `README.md` to document the new Fallback Strategy and project core updates.

## What Was Tested
- Unit tests added in `tests/test_error_classifier.py` ensuring combinations of common exact strings yield the expected enum values.
- `GeminiCLIModel` mocked subprocess unit test ensuring standard rate limit mock avoids retries.
- Re-run all tests (`pytest tests/ -v`).

## Validation Results
- ✅ All 117 tests passing cleanly (`117 passed, 2 warnings`).
