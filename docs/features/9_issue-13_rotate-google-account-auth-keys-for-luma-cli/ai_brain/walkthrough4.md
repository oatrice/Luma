# Metrics Integrity & Reliability Fixes

We have successfully addressed the data integrity issues in Luma metrics by enforcing authoritative synchronization with GitHub.

## Key Fixes

### 1. Mandays Reliability (#110, #14)
- **Problem**: Stale `actual_mandays` values (e.g., 7.5 for #110) caused by logic not re-calculating after date adjustments.
- **Solution**: Updated `IssueMetricsRecord.validate()` to force-recalculate `actual_mandays` whenever `start_datetime` and `actual_completion_date` are available.
- **Result**: Issue #110 corrected from **7.5** to **0.5**.

### 4. Duplicate/Obsolete Handling (#35)
- **Problem**: Issues closed as "Not Planned" (Duplicate/Obsolete) were still being counted as `✅ Complete` with accumulated mandays.
- **Solution**: Updated sync logic to check `stateReason`. Issues marked as `NOT_PLANNED` are now auto-set to status `🚫 Obsolete` with **0 mandays** and **0 points**.
- **Result**: Issue #35 corrected to **🚫 Obsolete** with **0.0 mandays**.

## Verification Results

A full sync of the `oatrice/TheMiddleWay-Metadata` project was performed after the final reliability fixes.

```text
Issue #110 (Corruption Fix):
  Status: ✅ Complete
  Old Mandays: 99.0 (Manual error)
  New Mandays: 0.5 (Auto-corrected from GH dates)

Issue #35 (Obsolete Fix):
  Status: 🚫 Obsolete (Synced from GH stateReason)
  Mandays: 0.0 (Zeroed out)

Issue #79 & #113 (Start Date Correction):
  - #79: 2.5 mandays (Start: 2026-03-13T16:55:20, End: 2026-03-16T05:46:46) 
  - #113: 1.0 manday (Start: 2026-03-20T13:04:48, End: 2026-03-21T10:55:41)
  - **Heuristic**: Luma now prioritizes "project_v2_item_status_changed" events performed by **human users**.
  - **Output**: Synced items now display "✨ Updated..." or "✅ Already up-to-date..." for transparency.
```

## Internal Cleanup & Reliability
- **Datetime Robustness**: Fixed a critical `AttributeError`/`TypeError` in `_start_is_placeholder` where string objects were being treated as datetime objects. 
- **Timezone Normalization**: Standardized `fetch_lane_transition_date` to return naive ISO strings, ensuring safe comparison with local metrics records.
- **Refactoring**: Modified `sync_github_metrics_for_project` to handle local data loading with `validate=False`, allowing recovery from corrupted `.luma_metrics.json` states.
