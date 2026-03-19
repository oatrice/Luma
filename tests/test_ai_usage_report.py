import runpy
from pathlib import Path


_REPORT_MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "ai_usage_report.py"),
    run_name="not_main",
)
build_report = _REPORT_MODULE["build_report"]


def test_build_report_includes_percentiles_and_error_breakdown():
    events = [
        {
            "event": "llm_call",
            "ts": "2026-03-19T00:00:00+00:00",
            "provider": "gemini_cli",
            "model": "gemini-2.5-flash",
            "status": "success",
            "duration_ms": 1000,
            "action": "Code Review",
        },
        {
            "event": "llm_call",
            "ts": "2026-03-19T00:01:00+00:00",
            "provider": "gemini_cli",
            "model": "gemini-2.5-flash",
            "status": "success",
            "duration_ms": 3000,
            "action": "Code Review",
        },
        {
            "event": "llm_call",
            "ts": "2026-03-19T00:02:00+00:00",
            "provider": "gemini_cli",
            "model": "gemini-2.5-flash",
            "status": "error",
            "duration_ms": 5000,
            "error_type": "TIMEOUT",
            "action": "Code Review",
        },
    ]

    report = build_report(events)

    assert "P50 ms" in report
    assert "P95 ms" in report
    assert "Error Breakdown" in report
    assert "TIMEOUT" in report
    assert "3000" in report


def test_build_report_handles_no_events():
    assert build_report([]) == "No AI usage events found."
