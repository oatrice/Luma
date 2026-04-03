## Summary

Guided Planning could fail during multi-issue runs for two separate reasons that surfaced in the same Zenith workflow:

1. `Analyst` and `Spec` built `docs/features/...` directory names directly from the combined multi-issue title, which could exceed filesystem basename limits and raise `File name too long`.
2. `FallbackModel` resumed from `FALLBACK_ACTIVE_INDEX` but only walked forward to the end of the configured model list, so a transient failure on the saved model could abort planning without retrying earlier models.

This PR fixes both failure modes by making feature directory naming filesystem-safe across planning agents and rotating fallback models in circular order. It also includes supporting telemetry and metrics cleanup that landed in the same branch.

## Changes

- Added `luma_core/feature_dirs.py` to centralize feature directory naming with slug sanitization, Thai transliteration, token compaction, byte-aware truncation, and hash suffixes for long titles.
- Updated `Analyst`, `Spec`, and `SBE` to use the shared feature-directory helper instead of building `docs/features/...` paths from raw multi-issue titles.
- Updated `FallbackModel` to try the configured model chain in circular order, starting from `FALLBACK_ACTIVE_INDEX` and wrapping back to earlier models before failing.
- Added regression coverage for long multi-issue feature directory names and fallback rotation when the saved model index points near the end of the chain.
- Added supporting telemetry and metrics updates included in this branch:
- Record headless action events and accept an optional `--caller` value.
- Filter non-`llm_call` events out of usage summaries and earliest-usage calculations.
- Prompt for missing post story points after workflow and metrics sync.
- Extend coverage for headless CLI, issue metrics, and metrics summarization.

## Impact

- Multi-issue Guided Planning no longer fails on overlong feature directory names when combined issue titles are very long.
- Planning now retries the full fallback chain even when the persisted active model is near the end of the list and fails transiently.
- `Analyst`, `Spec`, and `SBE` now generate consistent, filesystem-safe feature directories for multi-issue runs.
- Usage reporting remains accurate after adding action-level telemetry.

## Testing

- Added regression coverage in `tests/test_feature_dir_naming.py`
- Added regression coverage in `tests/test_llm_fallback_rotation.py`
- Added supporting coverage in `tests/test_main_headless_cli.py`
- Added supporting coverage in `tests/test_issue_metrics.py`
- Added supporting coverage in `tests/test_metrics_summarizer.py`

## Related

- https://github.com/oatrice/Zenith/issues/13
- https://github.com/oatrice/Zenith/issues/14
- https://github.com/oatrice/Zenith/issues/15
- https://github.com/oatrice/Zenith/issues/8

Closes https://github.com/oatrice/Luma/issues/35