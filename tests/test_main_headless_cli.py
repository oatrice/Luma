import json
from types import SimpleNamespace
from unittest.mock import Mock

import main

from luma_core.state_manager import LumaState, WorkflowPhase


def test_parse_cli_args_supports_headless_flags():
    args = main.parse_cli_args(
        ["--auto", "--action", "code_review", "--json", "--project", "1"]
    )

    assert args.auto is True
    assert args.action == "code_review"
    assert args.json is True
    assert args.project == "1"


def test_ensure_importlib_metadata_compat_adds_packages_distributions():
    fake_module = SimpleNamespace(distributions=lambda: [])

    main.ensure_importlib_metadata_compat(fake_module)

    assert callable(fake_module.packages_distributions)
    assert fake_module.packages_distributions() == {}


def test_headless_code_review_success_returns_json_only_on_stdout(
    monkeypatch, tmp_path, capsys
):
    project = {"name": "Headless Project", "path": str(tmp_path), "repo": "example/repo"}
    state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)
    calls = {}

    def fake_action(current_state, current_project, headless=False):
        print("action log should go to stderr")
        calls["state"] = current_state
        calls["project"] = current_project
        calls["headless"] = headless
        return {"summary": "review complete"}

    monkeypatch.setattr(main, "PROJECTS", {"1": project})
    monkeypatch.setattr(main, "load_state", lambda path: state)
    monkeypatch.setattr(main.actions, "action_code_review", fake_action)

    exit_code = main.main(
        ["--auto", "--action", "code_review", "--json", "--project", "1"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "status": "success",
        "action": "code_review",
        "project": "1",
        "result": {"summary": "review complete"},
    }
    assert "action log should go to stderr" not in captured.out
    assert "action log should go to stderr" in captured.err
    assert calls["state"] is state
    assert calls["project"] == project
    assert calls["headless"] is True


def test_headless_invalid_action_returns_json_error(monkeypatch, tmp_path, capsys):
    project = {"name": "Headless Project", "path": str(tmp_path), "repo": "example/repo"}
    state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)

    monkeypatch.setattr(main, "PROJECTS", {"1": project})
    monkeypatch.setattr(main, "load_state", lambda path: state)

    exit_code = main.main(
        ["--auto", "--action", "invalid_action", "--json", "--project", "1"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "error"
    assert payload["action"] == "invalid_action"
    assert payload["project"] == "1"
    assert "invalid_action" in payload["error"]


def test_headless_json_failure_returns_actionable_error(monkeypatch, tmp_path, capsys):
    project = {"name": "Headless Project", "path": str(tmp_path), "repo": "example/repo"}
    state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)

    def fake_action(current_state, current_project, headless=False):
        print("debug output should stay off stdout")
        raise RuntimeError("review execution failed")

    monkeypatch.setattr(main, "PROJECTS", {"1": project})
    monkeypatch.setattr(main, "load_state", lambda path: state)
    monkeypatch.setattr(main.actions, "action_code_review", fake_action)

    exit_code = main.main(
        ["--auto", "--action", "code_review", "--json", "--project", "1"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert payload == {
        "status": "error",
        "action": "code_review",
        "project": "1",
        "error": "review execution failed",
    }
    assert "debug output should stay off stdout" not in captured.out
    assert "debug output should stay off stdout" in captured.err


def test_interactive_mode_without_new_flags_still_uses_menu(monkeypatch, tmp_path):
    project = {"name": "Interactive Project", "path": str(tmp_path), "repo": "example/repo"}
    state = LumaState(project_key="test", phase=WorkflowPhase.IDLE)
    save_state_mock = Mock()
    display_header_mock = Mock()
    select_menu_mock = Mock(return_value="0")

    monkeypatch.setattr(main, "PROJECTS", {"test": project})
    monkeypatch.setattr(main, "load_global_config", lambda: {})
    monkeypatch.setattr(main, "save_global_config", lambda config: None)
    monkeypatch.setattr(main, "check_luma_outdated", lambda: (False, None))
    monkeypatch.setattr(main, "refresh_pending_doc_updates", lambda state, project: {})
    monkeypatch.setattr(main, "pending_doc_update_summary", lambda pending: "")
    monkeypatch.setattr(main, "detect_project_key_for_path", lambda current_cwd: "test")
    monkeypatch.setattr(main, "load_state", lambda path: state)
    monkeypatch.setattr(main, "save_state", save_state_mock)
    monkeypatch.setattr(main.ui, "display_header", display_header_mock)
    monkeypatch.setattr(main.ui, "select_menu_option", select_menu_mock)

    exit_code = main.main([])

    assert exit_code == 0
    display_header_mock.assert_called_once_with(state, project)
    select_menu_mock.assert_called_once()
    save_state_mock.assert_called_once_with(state, project["path"])
