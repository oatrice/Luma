# Luma Metrics Automation & Reliability

Checklist for fixing data integrity issues and enhancing GitHub sync.

- [x] Fix report generator safety net (gh_closed_at check)
- [\/] Fix mandays reliability (#110)
  - [x] Audit for discrepancies (found 17 issues)
  - [ ] Enforce re-calculation in `validate()`
- [ ] Sync GitHub Project status (#84)
  - [ ] Update `fetch_github_issue_details` to pull project lane
- [ ] Enhance `start_datetime` detection (#14)
  - [ ] Implement lane transition tracking via GitHub API
- [ ] Verify with report generation and auto-diff
