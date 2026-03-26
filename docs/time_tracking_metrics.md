# Time Tracking Metrics Dictionary

This document explains the time tracking fields stored in `.luma_metrics.json` to help project managers and data auditors accurately evaluate project performance and identify bottlenecks.

## Core Time Fields

### 1. `created_at`
- **Definition:** The exact timestamp when the issue was created in the upstream issue tracker (e.g., GitHub).
- **Source:** Synced from `gh issue view --json createdAt`.
- **Note:** For migrated issues, this field should be re-synced from GitHub to ensure linear time-series accuracy and avoid "Time Paradoxes" where an issue appears to complete before it was created.

### 2. `start_datetime`
- **Definition:** The timestamp denoting when actual work began on the issue.
- **Source:** 
  1. Ideally, derived from AI Usage Tracking logs (`.luma_ai_usage.jsonl`) which records the very first time an LLM was consulted for the issue.
  2. Fallback: The timestamp of the oldest Git commit referencing the issue number.
  3. Fallback for Local Time Paradoxes: Synthesized by subtracting `estimated_mandays` from the completion date.

### 3. `actual_completion_date`
- **Definition:** The timestamp recorded by the Luma CLI on the developer's local machine at the exact moment the issue was marked as `✅ Complete` in the local tracked state.
- **Characteristic:** Prone to "tracking delays" if the developer finishes the code but forgets to run Luma's completion workflow on their local machine.

### 4. `gh_closed_at`
- **Definition:** The absolute truth timestamp of when the issue was officially closed or the Pull Request was merged on GitHub.
- **Source:** Synced from `gh issue view --json closedAt`.
- **Characteristic:** The ultimate metric for organizational compliance and tracking execution lifecycle.

---

## Mandays Calculation Comparison

The system allows tracking effort via two comparative calculate fields to identify synchronization and performance gaps:

### `actual_mandays` (Local Effort)
- **Formula:** `(actual_completion_date - start_datetime) / 24 hours`
- **Use Case:** Reflects the developer's perceived time spent on the task from a local environment perspective. 

### `gh_mandays` (Absolute Effort)
- **Formula:** `(gh_closed_at - start_datetime) / 24 hours`
- **Use Case:** Reflects the organizational "Lead Time". If `gh_mandays` is significantly higher than `actual_mandays`, it indicates a "Tracking Discipline Gap" (e.g., the code was done locally 2 weeks ago, but the PR was left unmerged, or the developer forgot to close the ticket).

### Evaluating Tracking Discipline
By comparing `gh_mandays` vs `actual_mandays`, you can identify process bottlenecks:
- **Diff < 1 day:** Perfect sync. The developer merged and closed the issue promptly after local completion. (Note: A 0.3 day / 7-hour difference is typically just UTC vs +07:00 timezone shifting).
- **Diff > 2 days:** Process bottleneck. Work is completed but blocked in Code Review, QA, or poor ticket hygiene.

---

## GitHub Metrics Synchronization

### Automatic Sync (No Action Required)

The system automatically syncs `gh_closed_at` and `gh_mandays` from GitHub in the following situations:

| Trigger | When |
|---------|------|
| **Auto Full Workflow** finishes | Always, at the end of the guided workflow summary phase |
| **Generate Project Report** | Before every report generation |

### Manual Sync Options

Use manual sync only when needed (e.g., after editing `.luma_metrics.json` directly, or debugging):

| Option | How to Access |
|--------|--------------|
| `[Q] 🐙 Audit & Sync GitHub Metrics` | Main Luma CLI menu |
| `[4] Audit & Sync from GitHub` | `[M] Track Issue Metrics` sub-menu |

### Time Paradox Auto-Fix

A **"Time Paradox"** occurs when `actual_completion_date` is earlier than `start_datetime` (e.g., migrated issues with stale `created_at`).

**Resolution Strategy (applied automatically during sync):**
1. Detect if `actual_completion_date < start_datetime`
2. Shift `start_datetime` backward by `estimated_mandays` from `actual_completion_date`
3. Recalculate `gh_mandays` using the corrected `start_datetime`

### AI Usage Log Backfilling

If `start_datetime` is missing, the sync engine scans `.luma_ai_usage.jsonl` to find the **earliest recorded AI interaction** for the issue and uses that timestamp as `start_datetime`. This ensures that issues worked on before the formal workflow began are still tracked accurately.
