#!/usr/bin/env python3
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _load_events(path: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return events
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            if data.get("event") != "llm_call":
                continue
            events.append(data)
    return events


def _model_key(event: Dict[str, Any]) -> Tuple[str, str]:
    provider = event.get("provider") or "unknown"
    model = event.get("model") or event.get("model_type") or "unknown"
    return provider, model


def _issue_keys(event: Dict[str, Any]) -> List[Tuple[str, Optional[str]]]:
    issues = event.get("issues") or []
    if isinstance(issues, list) and issues:
        result = []
        for issue in issues:
            try:
                num = issue.get("number")
                title = issue.get("title")
                result.append((str(num), title))
            except Exception:
                continue
        if result:
            return result
    numbers = event.get("issue_numbers") or []
    if isinstance(numbers, list) and numbers:
        return [(str(n), None) for n in numbers]
    return [("none", None)]


def _add_stat(bucket: Dict[str, Any], event: Dict[str, Any]) -> None:
    bucket["total"] += 1
    status = event.get("status")
    if status == "success":
        bucket["success"] += 1
    elif status == "error":
        bucket["fail"] += 1
    duration_ms = event.get("duration_ms")
    if isinstance(duration_ms, (int, float)):
        bucket["duration_ms_total"] += float(duration_ms)
        bucket["duration_ms_count"] += 1


def _fmt_rate(success: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{round((success / total) * 100):d}%"


def _fmt_ms(total: float, count: int) -> str:
    if count <= 0:
        return "-"
    return f"{round(total / count):d}"


def _render_table(headers: List[str], rows: List[List[str]]) -> str:
    if not rows:
        return "(no data)"
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "-|-".join("-" * widths[i] for i in range(len(headers)))
    body_lines = [
        " | ".join(row[i].ljust(widths[i]) for i in range(len(headers)))
        for row in rows
    ]
    return "\n".join([header_line, sep_line] + body_lines)


def build_report(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "No AI usage events found."
    ts_values = [e.get("ts") for e in events if e.get("ts")]
    parsed_ts = [_parse_ts(t) for t in ts_values if isinstance(t, str)]
    parsed_ts = [t for t in parsed_ts if t is not None]
    range_text = "-"
    if parsed_ts:
        range_text = f"{min(parsed_ts).isoformat()} -> {max(parsed_ts).isoformat()}"

    overall = defaultdict(
        lambda: {
            "total": 0,
            "success": 0,
            "fail": 0,
            "duration_ms_total": 0.0,
            "duration_ms_count": 0,
        }
    )
    by_issue: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "title": None,
            "models": defaultdict(lambda: {"total": 0, "success": 0, "fail": 0}),
        }
    )
    by_action = defaultdict(lambda: {"total": 0, "success": 0, "fail": 0})

    for event in events:
        provider, model = _model_key(event)
        model_label = f"{provider} / {model}"
        _add_stat(overall[model_label], event)

        action = event.get("action") or "(unknown)"
        _add_stat(by_action[action], event)

        for issue_num, title in _issue_keys(event):
            issue_bucket = by_issue[issue_num]
            if title and not issue_bucket.get("title"):
                issue_bucket["title"] = title
            _add_stat(issue_bucket["models"][model_label], event)

    overall_rows = []
    for model_label, stats in sorted(
        overall.items(), key=lambda x: (-x[1]["total"], x[0])
    ):
        overall_rows.append(
            [
                model_label,
                str(stats["total"]),
                str(stats["success"]),
                str(stats["fail"]),
                _fmt_rate(stats["success"], stats["total"]),
                _fmt_ms(stats["duration_ms_total"], stats["duration_ms_count"]),
            ]
        )

    action_rows = []
    for action, stats in sorted(
        by_action.items(), key=lambda x: (-x[1]["total"], x[0])
    ):
        action_rows.append(
            [
                action,
                str(stats["total"]),
                str(stats["success"]),
                str(stats["fail"]),
                _fmt_rate(stats["success"], stats["total"]),
            ]
        )

    issue_blocks: List[str] = []
    for issue_num in sorted(by_issue.keys(), key=lambda x: (x == "none", x)):
        issue = by_issue[issue_num]
        title = issue.get("title") or ""
        header = f"Issue #{issue_num}" if issue_num != "none" else "Issue (none)"
        if title:
            header = f"{header} - {title}"
        rows = []
        for model_label, stats in sorted(
            issue["models"].items(), key=lambda x: (-x[1]["total"], x[0])
        ):
            rows.append(
                [
                    model_label,
                    str(stats["total"]),
                    str(stats["success"]),
                    str(stats["fail"]),
                    _fmt_rate(stats["success"], stats["total"]),
                ]
            )
        issue_blocks.append(
            "\n".join(
                [
                    header,
                    _render_table(
                        ["Model", "Total", "Success", "Fail", "Success%"], rows
                    ),
                ]
            )
        )

    lines = [
        "Luma AI Usage Report",
        f"Events: {len(events)}",
        f"Time Range: {range_text}",
        "",
        "Overall by Model",
        _render_table(
            ["Model", "Total", "Success", "Fail", "Success%", "Avg ms"], overall_rows
        ),
        "",
        "By Action",
        _render_table(["Action", "Total", "Success", "Fail", "Success%"], action_rows),
        "",
        "By Issue",
        "\n\n".join(issue_blocks),
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Luma AI usage report")
    parser.add_argument(
        "--log",
        default=None,
        help="Path to .luma_ai_usage.jsonl (defaults to repo root)",
    )
    args = parser.parse_args()

    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".luma_ai_usage.jsonl",
    )
    log_path = args.log or default_path

    events = _load_events(log_path)
    report = build_report(events)
    print(f"Log: {log_path}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
