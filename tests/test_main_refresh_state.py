import sys
from unittest.mock import Mock

import main

from luma_core.state_manager import IssueData, LumaState, WorkflowPhase
import luma_core.github_project as github_project


def test_refresh_state_skips_kanban_sync_when_project_id_missing_after_merge(
    monkeypatch, tmp_path
):
    project = {
        "name": "Luma",
        "path": str(tmp_path),
        "repo": "oatricedev/Luma",
    }
    state = LumaState(
        project_key="test",
        phase=WorkflowPhase.PR_PENDING,
        pr_url="https://github.com/oatrice/Zenith/pull/7",
        active_issues=[
            IssueData(
                number=7,
                title="Merged PR cleanup",
                html_url="https://github.com/oatrice/Zenith/issues/7",
                project_item_id="PVTI_123",
                project_id="",
            )
        ],
    )
    saved_states = []
    sync_mock = Mock()
    choices = iter(["R", "0"])

    monkeypatch.setattr(main, "PROJECTS", {"test": project})
    monkeypatch.setattr(main, "load_global_config", lambda: {})
    monkeypatch.setattr(main, "save_global_config", lambda config: None)
    monkeypatch.setattr(main, "check_luma_outdated", lambda: (False, None))
    monkeypatch.setattr(main, "refresh_pending_doc_updates", lambda state, project: {})
    monkeypatch.setattr(main, "pending_doc_update_summary", lambda pending: "")
    monkeypatch.setattr(main, "load_state", lambda path: state)
    monkeypatch.setattr(
        main,
        "save_state",
        lambda current_state, path: saved_states.append(current_state) or True,
    )
    monkeypatch.setattr(main, "get_status_workflow", lambda project: {"action_status_map": {}})
    monkeypatch.setattr(main.ui, "display_header", lambda state, project: None)
    monkeypatch.setattr(
        main.ui,
        "select_menu_option",
        lambda state, actions, title=None: next(choices),
    )
    monkeypatch.setattr(main.ui, "safe_input", lambda prompt="": "")
    monkeypatch.setattr(
        github_project,
        "check_pr_status_unified",
        lambda pr_url: {"merged": True, "state": "MERGED", "error": None},
    )
    monkeypatch.setattr(github_project, "sync_kanban_on_action", sync_mock)
    monkeypatch.setattr(sys, "argv", ["main.py", "--project", "test"])

    main.main()

    assert sync_mock.call_count == 0
    assert saved_states[-1].phase == WorkflowPhase.IDLE
