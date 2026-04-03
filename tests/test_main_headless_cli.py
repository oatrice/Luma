import json
import subprocess
import sys
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock

import main
import luma_core.usage_tracker as usage_tracker

from luma_core.state_manager import LumaState, WorkflowPhase


def _read_usage_events(log_path: Path):
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_parse_cli_args_supports_headless_flags():
    args = main.parse_cli_args(
        ["--auto", "--action", "code_review", "--json", "--project", "1"]
    )

    assert args.auto is True
    assert args.action == "code_review"
    assert args.json is True
    assert args.project == "1"


def test_parse_cli_args_supports_headless_alias():
    args = main.parse_cli_args(
        ["--headless", "--action", "code_review", "--json", "--project", "1"]
    )

    assert args.auto is True
    assert args.action == "code_review"
    assert args.json is True
    assert args.project == "1"


def test_parse_cli_args_supports_optional_caller_identifier():
    args = main.parse_cli_args(
        [
            "--auto",
            "--action",
            "code_review",
            "--json",
            "--project",
            "1",
            "--caller",
            "zenith-cli",
        ]
    )

    assert args.caller == "zenith-cli"


def test_parse_cli_args_supports_metadata_mode_without_action():
    args = main.parse_cli_args(["--meta", "--json"])

    assert args.meta is True
    assert args.json is True
    assert args.action is None
    assert args.auto is False


def test_metadata_mode_requires_json_when_invoked_via_main(capsys):
    exit_code = main.main(["--meta"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "--meta requires --json." in captured.err


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


def test_headless_code_review_success_records_action_level_log(
    monkeypatch, tmp_path, capsys
):
    project = {"name": "Headless Project", "path": str(tmp_path), "repo": "example/repo"}
    state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)
    log_path = tmp_path / ".luma_ai_usage.jsonl"

    def fake_action(current_state, current_project, headless=False):
        print("action log should go to stderr")
        return {"summary": "review complete"}

    monkeypatch.setattr(main, "PROJECTS", {"1": project})
    monkeypatch.setattr(main, "load_state", lambda path: state)
    monkeypatch.setattr(main.actions, "action_code_review", fake_action)
    monkeypatch.setattr(main.usage_tracker, "get_log_path", lambda: str(log_path))
    monkeypatch.setattr(main.usage_tracker, "_SESSION_ID", "headless123")
    monkeypatch.setattr(main.usage_tracker, "_get_luma_version", lambda: "1.7.0-test")

    usage_tracker.clear_action()
    usage_tracker.clear_context()

    exit_code = main.main(
        [
            "--auto",
            "--action",
            "code_review",
            "--json",
            "--project",
            "1",
            "--caller",
            "zenith-cli",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    events = _read_usage_events(log_path)
    action_events = [event for event in events if event.get("event") == "action_run"]

    assert exit_code == 0
    assert payload == {
        "status": "success",
        "action": "code_review",
        "project": "1",
        "result": {"summary": "review complete"},
    }
    assert len(action_events) == 1
    assert action_events[0]["mode"] == "headless"
    assert action_events[0]["action"] == "code_review"
    assert action_events[0]["project"] == "1"
    assert action_events[0]["status"] == "success"
    assert action_events[0]["exit_code"] == 0
    assert action_events[0]["session_id"] == "headless123"
    assert action_events[0]["caller"] == "zenith-cli"
    assert action_events[0]["error"] is None
    assert isinstance(action_events[0]["duration_ms"], int)
    assert action_events[0]["duration_ms"] >= 0
    assert "action log should go to stderr" not in captured.out
    assert "action log should go to stderr" in captured.err


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


def test_headless_json_failure_records_action_level_log(monkeypatch, tmp_path, capsys):
    project = {"name": "Headless Project", "path": str(tmp_path), "repo": "example/repo"}
    state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)
    log_path = tmp_path / ".luma_ai_usage.jsonl"

    def fake_action(current_state, current_project, headless=False):
        print("debug output should stay off stdout")
        raise RuntimeError("review execution failed")

    monkeypatch.setattr(main, "PROJECTS", {"1": project})
    monkeypatch.setattr(main, "load_state", lambda path: state)
    monkeypatch.setattr(main.actions, "action_code_review", fake_action)
    monkeypatch.setattr(main.usage_tracker, "get_log_path", lambda: str(log_path))
    monkeypatch.setattr(main.usage_tracker, "_SESSION_ID", "headless123")
    monkeypatch.setattr(main.usage_tracker, "_get_luma_version", lambda: "1.7.0-test")

    usage_tracker.clear_action()
    usage_tracker.clear_context()

    exit_code = main.main(
        ["--auto", "--action", "code_review", "--json", "--project", "1"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    events = _read_usage_events(log_path)
    action_events = [event for event in events if event.get("event") == "action_run"]

    assert exit_code == 2
    assert payload == {
        "status": "error",
        "action": "code_review",
        "project": "1",
        "error": "review execution failed",
    }
    assert len(action_events) == 1
    assert action_events[0]["mode"] == "headless"
    assert action_events[0]["action"] == "code_review"
    assert action_events[0]["project"] == "1"
    assert action_events[0]["status"] == "error"
    assert action_events[0]["exit_code"] == 2
    assert action_events[0]["session_id"] == "headless123"
    assert action_events[0]["error"] == "review execution failed"
    assert "caller" not in action_events[0]
    assert isinstance(action_events[0]["duration_ms"], int)
    assert action_events[0]["duration_ms"] >= 0
    assert "debug output should stay off stdout" not in captured.out
    assert "debug output should stay off stdout" in captured.err


def test_metadata_mode_returns_machine_readable_payload(monkeypatch, capsys):
    monkeypatch.setattr(main, "CONTRACT_VERSION", "2026-04-02")
    monkeypatch.setattr(main, "SUPPORTED_HEADLESS_ACTIONS", ("code_review",))
    monkeypatch.setattr(main, "get_current_version", lambda *args: "1.6.0")
    monkeypatch.setattr(
        main,
        "get_project_git_info",
        lambda path: {"hash": "abc123def456", "date": "2026-04-02 09:32:45 +0700"},
    )
    monkeypatch.setattr(main, "is_git_dirty", lambda path: True)
    monkeypatch.setattr(main.platform, "python_version", lambda: "3.9.6")

    exit_code = main.main(["--meta", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "status": "success",
        "mode": "metadata",
        "result": {
            "version": "1.6.0",
            "git_commit": "abc123def456",
            "dirty": True,
            "contract_version": "2026-04-02",
            "supported_actions": ["code_review"],
            "python_version": "3.9.6",
        },
    }
    assert captured.err == ""


def test_metadata_mode_rejects_action_arguments(capsys):
    exit_code = main.main(["--meta", "--json", "--action", "code_review"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert payload == {
        "status": "error",
        "action": "code_review",
        "project": "1",
        "error": "--meta cannot be combined with --action, --auto, or --headless.",
    }


def test_real_subprocess_headless_json_stdout_remains_parseable():
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "main.py"),
            "--auto",
            "--action",
            "invalid_action",
            "--json",
            "--project",
            "12",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["status"] == "error"
    assert payload["action"] == "invalid_action"
    assert payload["project"] == "12"
    assert "invalid_action" in payload["error"]


def test_real_subprocess_supported_action_keeps_stdout_json_only(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    inline_script = textwrap.dedent(
        f"""
        import main
        from luma_core.state_manager import LumaState, WorkflowPhase

        project = {{"name": "Subprocess Project", "path": {str(tmp_path)!r}, "repo": "example/repo"}}
        state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)

        main.PROJECTS = {{"1": project}}
        main.load_state = lambda path: state

        def fake_action(current_state, current_project, headless=False):
            print("subprocess diagnostic should stay off stdout")
            return {{"summary": "ok", "headless": headless, "project_name": current_project["name"]}}

        main.actions.action_code_review = fake_action

        raise SystemExit(
            main.main(["--auto", "--action", "code_review", "--json", "--project", "1"])
        )
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", inline_script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload == {
        "status": "success",
        "action": "code_review",
        "project": "1",
        "result": {
            "summary": "ok",
            "headless": True,
            "project_name": "Subprocess Project",
        },
    }
    assert "subprocess diagnostic should stay off stdout" not in result.stdout
    assert "subprocess diagnostic should stay off stdout" in result.stderr


def test_headless_alias_supported_action_keeps_stdout_json_only(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    inline_script = textwrap.dedent(
        f"""
        import main
        from luma_core.state_manager import LumaState, WorkflowPhase

        project = {{"name": "Alias Project", "path": {str(tmp_path)!r}, "repo": "example/repo"}}
        state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)

        main.PROJECTS = {{"1": project}}
        main.load_state = lambda path: state

        def fake_action(current_state, current_project, headless=False):
            print("alias diagnostic should stay off stdout")
            return {{"summary": "alias-ok", "headless": headless}}

        main.actions.action_code_review = fake_action

        raise SystemExit(
            main.main(["--headless", "--action", "code_review", "--json", "--project", "1"])
        )
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", inline_script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload == {
        "status": "success",
        "action": "code_review",
        "project": "1",
        "result": {
            "summary": "alias-ok",
            "headless": True,
        },
    }
    assert "alias diagnostic should stay off stdout" not in result.stdout
    assert "alias diagnostic should stay off stdout" in result.stderr


def test_zenith_style_consumer_still_parses_headless_json_after_action_logging(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    log_path = tmp_path / ".luma_ai_usage.jsonl"
    inner_script = textwrap.dedent(
        f"""
        import main
        import luma_core.usage_tracker as usage_tracker
        from luma_core.state_manager import LumaState, WorkflowPhase

        project = {{"name": "Zenith Project", "path": {str(tmp_path)!r}, "repo": "example/repo"}}
        state = LumaState(project_key="1", phase=WorkflowPhase.IDLE)

        main.PROJECTS = {{"1": project}}
        main.load_state = lambda path: state
        usage_tracker.get_log_path = lambda: {str(log_path)!r}
        usage_tracker._SESSION_ID = "zenith123"

        def fake_action(current_state, current_project, headless=False):
            print("zenith diagnostic should stay off stdout")
            return {{"summary": "ok"}}

        main.actions.action_code_review = fake_action

        raise SystemExit(
            main.main(
                [
                    "--auto",
                    "--action",
                    "code_review",
                    "--json",
                    "--project",
                    "1",
                    "--caller",
                    "zenith-wrapper",
                ]
            )
        )
        """
    )
    wrapper_script = textwrap.dedent(
        f"""
        import json
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-c", {inner_script!r}],
            capture_output=True,
            text=True,
            check=False,
        )

        payload = json.loads(result.stdout)
        print(
            json.dumps(
                {{
                    "status": payload["status"],
                    "action": payload["action"],
                    "project": payload["project"],
                    "returncode": result.returncode,
                }}
            )
        )
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", wrapper_script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    action_events = [
        event for event in _read_usage_events(log_path) if event.get("event") == "action_run"
    ]

    assert result.returncode == 0
    assert payload == {
        "status": "success",
        "action": "code_review",
        "project": "1",
        "returncode": 0,
    }
    assert len(action_events) == 1
    assert action_events[0]["caller"] == "zenith-wrapper"


def test_readme_documents_metadata_and_stdout_contract():
    readme = Path(__file__).resolve().parents[1] / "README.md"
    content = readme.read_text(encoding="utf-8")

    assert "Headless CLI Contract" in content
    assert "python main.py --meta --json" in content
    assert "--headless" in content
    assert "stdout" in content
    assert "stderr" in content


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
