import json

import luma_core.usage_tracker as usage_tracker


def test_record_llm_event_includes_luma_version(tmp_path, monkeypatch):
    log_path = tmp_path / ".luma_ai_usage.jsonl"

    monkeypatch.setattr(usage_tracker, "get_log_path", lambda: str(log_path))
    monkeypatch.setattr(usage_tracker, "_build_context", lambda: {})
    monkeypatch.setattr(usage_tracker, "_get_luma_version", lambda: "1.3.0-test")

    usage_tracker.clear_action()
    usage_tracker.clear_context()
    usage_tracker.record_llm_event(
        provider="gemini-cli",
        model="gemini-2.5-pro",
        status="success",
    )

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    event = json.loads(lines[0])
    assert event["luma_version"] == "1.3.0-test"
    assert event["status"] == "success"
    assert event["provider"] == "gemini-cli"


def test_get_luma_version_returns_unknown_when_version_file_missing(monkeypatch):
    monkeypatch.setattr(usage_tracker, "_LUMA_VERSION_CACHE", None)
    monkeypatch.setattr(usage_tracker.os.path, "exists", lambda _path: False)

    assert usage_tracker._get_luma_version() == "unknown"


def test_record_llm_event_includes_error_type(tmp_path, monkeypatch):
    log_path = tmp_path / ".luma_ai_usage.jsonl"

    monkeypatch.setattr(usage_tracker, "get_log_path", lambda: str(log_path))
    monkeypatch.setattr(usage_tracker, "_build_context", lambda: {})

    usage_tracker.clear_action()
    usage_tracker.clear_context()
    usage_tracker.record_llm_event(
        provider="gemini-cli",
        model="gemini-2.5-pro",
        status="error",
        error="Some error message",
        error_type="RATE_LIMIT",
    )

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    event = json.loads(lines[0])
    assert event["status"] == "error"
    assert event["error_type"] == "RATE_LIMIT"


def test_get_current_sub_action():
    usage_tracker.clear_sub_action()
    assert usage_tracker.get_current_sub_action() is None

    usage_tracker.set_sub_action("Test/SubAction")
    assert usage_tracker.get_current_sub_action() == "Test/SubAction"

    usage_tracker.clear_sub_action()
