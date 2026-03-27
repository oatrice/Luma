"""Tests for luma_core.metrics_summarizer — TDD RED phase."""
import json
import os
import tempfile

from luma_core.metrics_summarizer import (
    summarize_usage_stats,
    summarize_issue_metrics,
    format_summary_message,
)


def _write_jsonl(path, events):
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


# ──────────────────────────────────────────────
# 1. summarize_usage_stats
# ──────────────────────────────────────────────

def test_summarize_usage_stats_basic():
    events = [
        {"ts": "2026-03-21T10:00:00", "event": "llm_call", "status": "success",
         "model": "gemini-2.5-pro", "provider": "gemini_cli",
         "duration_ms": 5000, "action": "Auto Full Workflow",
         "project_name": "MyProject", "session_id": "abc123"},
        {"ts": "2026-03-21T10:01:00", "event": "llm_call", "status": "error",
         "model": "gemini-2.5-pro", "provider": "gemini_cli",
         "duration_ms": 2000, "action": "Auto Full Workflow",
         "project_name": "MyProject", "session_id": "abc123"},
        {"ts": "2026-03-21T10:02:00", "event": "llm_call", "status": "success",
         "model": "gemini-3-flash-preview", "provider": "gemini_cli",
         "duration_ms": 3000, "action": "Refine Issue",
         "project_name": "MyProject", "session_id": "abc123"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
        path = f.name

    try:
        result = summarize_usage_stats(path)
        assert result["total_calls"] == 3
        assert result["success_count"] == 2
        assert result["error_count"] == 1
        assert result["total_duration_ms"] == 10000
        assert "elapsed_ms" in result
        assert result["elapsed_ms"] >= 120000  # 10:02:00 - 10:00:00 = 2 mins
        assert "success_rate" in result
        assert result["success_rate"] == 66.7
        assert len(result["unique_models"]) == 2
        assert "gemini-2.5-pro" in result["unique_models"]
    finally:
        os.unlink(path)


def test_summarize_usage_stats_project_filter():
    events = [
        {"ts": "2026-03-21T10:00:00", "event": "llm_call", "status": "success",
         "model": "m1", "duration_ms": 1000,
         "project_name": "Alpha"},
        {"ts": "2026-03-21T10:01:00", "event": "llm_call", "status": "success",
         "model": "m2", "duration_ms": 2000,
         "project_name": "Beta"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
        path = f.name

    try:
        result = summarize_usage_stats(path, project={"name": "Alpha"})
        assert result["total_calls"] == 1
        assert result["total_duration_ms"] == 1000
    finally:
        os.unlink(path)


# ──────────────────────────────────────────────
# 2. summarize_issue_metrics
# ──────────────────────────────────────────────

def test_summarize_issue_metrics_basic():
    store = {
        "version": "1.0",
        "issues": {
            "repo#1": {
                "issue_key": "repo#1", "issue_number": 1,
                "issue_title": "Feature A", "issue_url": "",
                "repository": "repo",
                "issue_status": "✅ Done",
                "estimate_points": 3, "estimated_mandays": 3.0,
                "actual_mandays": 2.5,
            },
            "repo#2": {
                "issue_key": "repo#2", "issue_number": 2,
                "issue_title": "Feature B", "issue_url": "",
                "repository": "repo",
                "issue_status": "🔲 Todo",
                "estimate_points": 5, "estimated_mandays": 5.0,
                "actual_mandays": 0.0,
            },
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(store, f)
        path = f.name

    try:
        result = summarize_issue_metrics(path)
        assert result["total_issues"] == 2
        assert result["done_count"] == 1
        assert result["total_points"] == 8
        assert result["total_estimated_mandays"] == 8.0
        assert result["total_actual_mandays"] == 2.5
    finally:
        os.unlink(path)


# ──────────────────────────────────────────────
# 3. format_summary_message
# ──────────────────────────────────────────────

def test_format_summary_message():
    usage = {
        "total_calls": 10,
        "success_count": 8,
        "error_count": 2,
        "total_duration_ms": 60000,
        "unique_models": ["gemini-2.5-pro", "gemini-3-flash"],
        "top_actions": {"Auto Full Workflow": 5, "Refine Issue": 3},
    }
    metrics = {
        "total_issues": 5,
        "done_count": 3,
        "in_progress_count": 1,
        "todo_count": 1,
        "total_points": 21,
        "total_estimated_mandays": 15.0,
        "total_actual_mandays": 10.5,
    }
    msg = format_summary_message(usage, metrics)
    assert "10" in msg  # total calls
    assert "8" in msg   # success
    assert "21" in msg  # points
    assert "1m 0s" in msg  # duration formatted
    assert isinstance(msg, str)
    assert len(msg) > 50  # non-trivial message
def test_format_summary_message_expanded():
    usage = {
        "total_calls": 20,
        "success_count": 15,
        "error_count": 5,
        "success_rate": 75.0,
        "total_duration_ms": 120000,
        "elapsed_ms": 300000,  # 5 mins
        "unique_models": ["gemini-2.5-pro", "gemini-3-flash"],
        "model_counts": {"gemini-2.5-pro": 12, "gemini-3-flash": 8},
        "top_actions": {
            "Action1": 5, "Action2": 4, "Action3": 3, "Action4": 2, "Action5": 1,
            "Action6": 1, "Action7": 1, "Action8": 1, "Action9": 1, "Action10": 1
        },
    }
    metrics = {
        "total_issues": 5,
        "done_count": 3,
        "in_progress_count": 1,
        "todo_count": 1,
        "total_points": 21,
        "total_estimated_mandays": 15.0,
        "total_actual_mandays": 10.5,
    }
    msg = format_summary_message(usage, metrics)
    
    # Check for new sections/info
    assert "Success Rate: 75.0%" in msg
    assert "Workflow Duration: 5m 0s" in msg
    assert "AI Processing Time: 2m 0s" in msg
    assert "Model Breakdown" in msg
    assert "gemini-2.5-pro (12)" in msg
    assert "Action10 (1)" in msg
    assert len(msg) > 100
