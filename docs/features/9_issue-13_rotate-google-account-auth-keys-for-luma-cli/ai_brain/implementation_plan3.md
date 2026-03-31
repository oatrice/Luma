# Automating Luma Metrics & Time Paradox Auto-fix

This plan outlines how we will seamlessly integrate the new GitHub fields (`gh_closed_at`, `gh_mandays`) into Luma's native workflows, ensuring metrics are always accurate and synchronized without introducing performance overhead.

## Proposed Changes

### 1. `luma_core/issue_metrics.py` (Core Logic)
Modify the main metrics record and add the synchronization logic:
- Update `IssueMetricsRecord` dataclass to include `gh_closed_at` and `gh_mandays`.
- Create a new batch function `sync_github_metrics_for_project(project_path)`:
  - Invokes `gh issue list --state all --json number,createdAt,closedAt --limit 200` to fetch data in bulk (avoiding slow per-issue network calls).
  - Updates tracked issues with `gh_closed_at` and `created_at`.
  - Calculates `gh_mandays` based on `gh_closed_at` and `start_datetime`.
  - Automatically detects **Time Paradoxes** (`actual_completion_date < start_datetime`) and silently corrects `start_datetime` utilizing the `estimated_mandays`.

### 2. `luma_core/actions/workflow_actions.py` (Guided Workflow Auto-Sync)
- **Auto-Sync:** Inside `action_guided_workflow()`, right before step 8 sends the Telegram Summary, call `sync_github_metrics_for_project()`. This ensures whenever the user finishes a feature development cycle, the GitHub closure times are downloaded and Time Paradoxes are fixed instantly.

### 3. `luma_core/actions/metrics_actions.py` (Report & Manual Sync)
- **Report Hook:** Inside `action_generate_project_report()`, right after `prefill_metrics_from_roadmap`, call `sync_github_metrics_for_project()`.
- **Manual Sync:** Inside `action_manage_issue_metrics()`, add a new menu option `[4] Audit & Sync GitHub Metrics` so the user can manually trigger it.

## Verification Plan

### Automated Tests
- N/A - The changes heavily rely on the developer's local GitHub CLI authentication (`gh`).

### Manual Verification
- Open Luma CLI (`luma`) in "The Middle Way".
- Navigate to `Track Issue Metrics` -> `Audit & Sync GitHub Metrics` and verify successful extraction and patching.
- Navigate to `Generate Project Report` -> `Weekly Report` and confirm the sync hook runs automatically before report construction.
