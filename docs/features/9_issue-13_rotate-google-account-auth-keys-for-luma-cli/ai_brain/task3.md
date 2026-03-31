# Luma Metrics Automation Update

Checklist to implement robust automated and manual syncing for `gh_closed_at` and `gh_mandays`.

- [ ] Inspect existing `luma_cli.py` and `report_generator.py` for integration points.
- [ ] Implement `sync_github_close_dates()` and `fix_time_paradoxes()` inside `luma_core/issue_metrics.py`.
- [ ] Hook the new syncing functions into the standard Luma workflow (e.g., Report Generation / Step 9).
- [ ] Add an explicit "Audit & Sync Luma Metrics" option to the Admin/Utility menu in Luma CLI.
- [ ] Test the new manual CLI command and the auto-trigger mechanism.
