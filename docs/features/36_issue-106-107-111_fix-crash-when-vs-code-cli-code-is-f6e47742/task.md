# Task List for Issues #106, #107, #111

- [x] Fix `#106`/`#107`: Add `try-except FileNotFoundError` around `subprocess.run(["code", "--diff", ...])` in `luma_core/tools.py`.
- [x] Create test `tests/test_tools_code_diff.py` to ensure Luma handles missing `code` CLI gracefully without crashing.
- [x] Fix `#111`: Update `action_guided_workflow` inside `luma_core/actions/workflow_actions.py` to prompt `[f] Force Export Prompt Only`.
- [x] Update `action_create_pr` signature to accept `force_export_only`.
- [x] Update `action_create_pr` to skip PR check if `force_export_only` is true.
- [x] Update `action_create_pr` to use `existing.get('url')` fallback.
- [x] Update `action_create_pr` to pass `force_export_only` in `pub_state`.
- [x] Update `publisher_agent` in `luma_core/agents/publisher.py` to abort after saving prompt if `force_export_only` is true.
- [x] Write a test `tests/test_pr_force_export.py` to verify this behavior.
- [x] Verify changes locally (run pytest).
