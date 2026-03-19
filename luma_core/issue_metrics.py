from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from typing import Dict, List, Optional


METRICS_FILENAME = ".luma_metrics.json"
EFFORT_LEVELS = ("Low", "Medium", "High")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def issue_key_for(repository: str, issue_number: int) -> str:
    repo = (repository or "").strip()
    if repo:
        return f"{repo}#{issue_number}"
    return str(issue_number)


def parse_metric_datetime(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError("Date/time is required.")

    candidates = [text]
    if " " in text and "T" not in text:
        candidates.append(text.replace(" ", "T", 1))

    formats = (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
    )

    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if "T" not in candidate and " " not in candidate:
                continue
            return dt.isoformat(timespec="seconds")
        except ValueError:
            pass

    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.isoformat(timespec="seconds")
        except ValueError:
            continue

    raise ValueError("Use date/time format like 2026-03-19 14:30.")


def format_metric_datetime(value: Optional[str]) -> str:
    if not value:
        return "-"
    return value.replace("T", " ")[:19]


def validate_estimate_points(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Estimate Points must be an integer.")
    if value < 0:
        raise ValueError("Estimate Points must be 0 or greater.")
    return value


def validate_mandays(value: Optional[float], field_name: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric.")
    if value < 0:
        raise ValueError(f"{field_name} must be 0 or greater.")
    return float(value)


def validate_effort_level(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = (value or "").strip()
    if not text:
        return None
    normalized = text.lower()
    for allowed in EFFORT_LEVELS:
        if normalized == allowed.lower():
            return allowed
    raise ValueError("Effort Level must be Low, Medium, or High.")


@dataclass
class IssueMetricsRecord:
    issue_key: str
    issue_number: int
    issue_title: str
    issue_url: str
    repository: str
    project_name: Optional[str] = None
    issue_status: Optional[str] = None
    estimate_points: Optional[int] = None
    estimated_mandays: Optional[float] = None
    actual_mandays: Optional[float] = None
    due_date: Optional[str] = None
    actual_completion_date: Optional[str] = None
    effort_level: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def validate(self) -> "IssueMetricsRecord":
        self.estimate_points = validate_estimate_points(self.estimate_points)
        self.estimated_mandays = validate_mandays(
            self.estimated_mandays, "Estimated Mandays"
        )
        self.actual_mandays = validate_mandays(self.actual_mandays, "Actual Mandays")
        self.effort_level = validate_effort_level(self.effort_level)
        if self.due_date:
            self.due_date = parse_metric_datetime(self.due_date)
        if self.actual_completion_date:
            self.actual_completion_date = parse_metric_datetime(
                self.actual_completion_date
            )
        return self

    def to_dict(self) -> Dict[str, object]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "IssueMetricsRecord":
        record = cls(**data)
        return record.validate()


def get_metrics_path(project_path: str) -> str:
    return os.path.join(project_path, METRICS_FILENAME)


def load_metrics_store(project_path: str) -> Dict[str, object]:
    path = get_metrics_path(project_path)
    if not os.path.exists(path):
        return {"version": "1.0", "issues": {}}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return {"version": "1.0", "issues": {}}

    issues = data.get("issues")
    if not isinstance(issues, dict):
        issues = {}

    return {
        "version": str(data.get("version", "1.0")),
        "issues": issues,
    }


def save_metrics_store(project_path: str, store: Dict[str, object]) -> None:
    os.makedirs(project_path, exist_ok=True)
    path = get_metrics_path(project_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def list_issue_metrics(project_path: str) -> List[IssueMetricsRecord]:
    store = load_metrics_store(project_path)
    records: List[IssueMetricsRecord] = []
    for item in store.get("issues", {}).values():
        if not isinstance(item, dict):
            continue
        try:
            records.append(IssueMetricsRecord.from_dict(item))
        except (TypeError, ValueError):
            continue

    records.sort(key=lambda record: record.updated_at or "", reverse=True)
    return records


def get_issue_metrics(
    project_path: str, repository: str, issue_number: int
) -> Optional[IssueMetricsRecord]:
    store = load_metrics_store(project_path)
    item = store.get("issues", {}).get(issue_key_for(repository, issue_number))
    if not isinstance(item, dict):
        return None
    return IssueMetricsRecord.from_dict(item)


def save_issue_metrics(project_path: str, record: IssueMetricsRecord) -> IssueMetricsRecord:
    store = load_metrics_store(project_path)
    issues = store.setdefault("issues", {})
    existing = issues.get(record.issue_key)

    if isinstance(existing, dict) and existing.get("created_at"):
        record.created_at = existing["created_at"]

    record.updated_at = _now_iso()
    issues[record.issue_key] = record.to_dict()
    save_metrics_store(project_path, store)
    return record
