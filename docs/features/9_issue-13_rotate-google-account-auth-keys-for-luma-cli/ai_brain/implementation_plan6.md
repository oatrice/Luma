# Goal: Expand Telegram Summary Message

Increase the detail and length of the summary message sent to Telegram after a workflow completes to provide more useful insights.

## Proposed Changes

### Luma Core Metrics Summarizer

#### [MODIFY] [metrics_summarizer.py](file:///Users/oatrice/Software-projects/Luma/luma_core/metrics_summarizer.py)
- Update `summarize_usage_stats`:
    - Capture `min(ts)` and `max(ts)` to calculate **Elapsed Duration** (Wall-clock time).
    - Return `elapsed_ms` in the result dictionary.
    - Return more than 5 top actions (e.g., 10).
    - Add `success_rate` calculation.
- Update `format_summary_message`:
    - Include **Workflow Duration** (Elapsed Time) in addition to AI Processing Time.
    - Include **Success Rate (%)**.
    - Show more **Top Actions** (up to 10).
    - Add a **Model Breakdown** section (counts per model).
    - Make the message significantly longer and more detailed (Premium look).

## Verification Plan

### Automated Tests
- Run `pytest tests/test_metrics_summarizer.py` to ensure existing tests pass.
- Add a new test case `test_format_summary_message_expanded` in `tests/test_metrics_summarizer.py` that checks for the new fields (Success Rate, extended Action list).

```bash
pytest tests/test_metrics_summarizer.py
```

### Manual Verification
- I can call the `format_summary_message` function with mock data in a scratch script and print the output to verify the look and feel.
