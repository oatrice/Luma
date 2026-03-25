from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
import json
import os
import re
import subprocess
from typing import Dict, List, Optional


METRICS_FILENAME = ".luma_metrics.json"
EFFORT_LEVELS = ("Low", "Medium", "High")
MATCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "to",
    "for",
    "of",
    "in",
    "on",
    "with",
    "from",
    "by",
    "vs",
    "via",
    "new",
    "add",
    "added",
    "update",
    "updated",
    "improve",
    "improved",
    "improving",
    "docs",
    "doc",
    "documentation",
    "feature",
    "epic",
    "bug",
    "setup",
    "follow",
    "followup",
    "todo",
    "complete",
    "completed",
    "ready",
    "project",
    "issue",
    "status",
    "plan",
    "analysis",
    "spec",
    "sbe",
    "admin",
    "web",
    "ios",
    "android",
    "backend",
    "root",
}


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


def get_changelog_path(project_path: str) -> Optional[str]:
    candidates = [
        os.path.join(project_path, "docs", "CHANGELOG.md"),
        os.path.join(project_path, "CHANGELOG.md"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


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


def get_roadmap_path(project_path: str) -> Optional[str]:
    candidates = [
        os.path.join(project_path, "docs", "ROADMAP.md"),
        os.path.join(project_path, "ROADMAP.md"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _extract_issue_numbers(text: str) -> List[int]:
    numbers = {
        int(match.group(1))
        for match in re.finditer(r"(?:issue\s*#|#)(\d+)\b", text or "", re.IGNORECASE)
    }
    return sorted(numbers)


def _normalize_match_token(token: str) -> str:
    normalized = (token or "").strip().lower()
    if len(normalized) > 4 and normalized.endswith("ies"):
        normalized = normalized[:-3] + "y"
    elif len(normalized) > 4 and normalized.endswith("es"):
        normalized = normalized[:-2]
    elif len(normalized) > 3 and normalized.endswith("s"):
        normalized = normalized[:-1]
    return normalized


def _tokenize_for_match(text: str) -> List[str]:
    tokens: List[str] = []
    for raw in re.split(r"[^0-9A-Za-zก-๙]+", (text or "").lower()):
        if not raw:
            continue
        token = _normalize_match_token(raw)
        if len(token) < 3 or token in MATCH_STOPWORDS:
            continue
        tokens.append(token)
    return tokens


def _normalize_git_datetime(raw_value: str) -> Optional[str]:
    text = (raw_value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt.isoformat(timespec="seconds")


def _date_to_end_of_day(day: date) -> str:
    return datetime.combine(day, time(23, 59, 59)).isoformat(timespec="seconds")


def _date_to_completion_anchor(day: date) -> str:
    return datetime.combine(day, time(18, 0, 0)).isoformat(timespec="seconds")


def _parse_date_only(text: str) -> Optional[date]:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _estimate_release_cadence_days(release_dates: List[date]) -> int:
    unique_dates = sorted(set(release_dates))
    if len(unique_dates) < 2:
        return 7

    deltas = [
        (current - previous).days
        for previous, current in zip(unique_dates, unique_dates[1:])
        if (current - previous).days > 0
    ]
    if not deltas:
        return 7

    deltas.sort()
    return max(1, deltas[len(deltas) // 2])


def _parse_changelog_evidence(project_path: str) -> Dict[str, object]:
    changelog_path = get_changelog_path(project_path)
    if not changelog_path:
        return {"release_dates": [], "issue_dates": {}, "entries": []}

    release_heading_re = re.compile(r"^##\s+\[[^\]]+\]\s*-\s*(\d{4}-\d{2}-\d{2})")
    release_dates: List[date] = []
    issue_dates: Dict[int, date] = {}
    entries: List[Dict[str, object]] = []
    current_release_date: Optional[date] = None

    with open(changelog_path, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            release_match = release_heading_re.match(line)
            if release_match:
                current_release_date = _parse_date_only(release_match.group(1))
                if current_release_date:
                    release_dates.append(current_release_date)
                continue

            if not current_release_date or not line or line.startswith("```"):
                continue
            if line.startswith("##"):
                continue

            issue_numbers = _extract_issue_numbers(line)
            tokens = _tokenize_for_match(line)
            entries.append(
                {
                    "date": current_release_date,
                    "text": line,
                    "issue_numbers": issue_numbers,
                    "tokens": tokens,
                }
            )

            for issue_number in issue_numbers:
                existing = issue_dates.get(issue_number)
                if existing is None or current_release_date > existing:
                    issue_dates[issue_number] = current_release_date

    return {
        "release_dates": release_dates,
        "issue_dates": issue_dates,
        "entries": entries,
    }


def _parse_git_history_evidence(project_path: str) -> Dict[str, object]:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                project_path,
                "log",
                "--all",
                "--date=iso-strict",
                "--pretty=format:%cI\t%s",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {"issue_dates": {}, "commits": []}

    issue_dates: Dict[int, str] = {}
    commits: List[Dict[str, object]] = []

    for line in result.stdout.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        raw_date, subject = line.split("\t", 1)
        commit_date = _normalize_git_datetime(raw_date)
        if not commit_date:
            continue

        issue_numbers = _extract_issue_numbers(subject)
        tokens = _tokenize_for_match(subject)
        commits.append(
            {
                "date": commit_date,
                "text": subject,
                "issue_numbers": issue_numbers,
                "tokens": tokens,
            }
        )

        for issue_number in issue_numbers:
            existing = issue_dates.get(issue_number)
            if existing is None or commit_date > existing:
                issue_dates[issue_number] = commit_date

    return {
        "issue_dates": issue_dates,
        "commits": commits,
    }


def _best_fuzzy_date_match(
    title: str,
    entries: List[Dict[str, object]],
    minimum_overlap: int,
) -> Optional[object]:
    title_tokens = set(_tokenize_for_match(title))
    if not title_tokens:
        return None

    best_value = None
    best_score = 0

    for entry in entries:
        entry_tokens = set(entry.get("tokens", []))
        overlap = len(title_tokens & entry_tokens)
        if overlap < minimum_overlap:
            continue

        value = entry.get("date")
        is_better_value = bool(value) and (best_value is None or value > best_value)
        if overlap > best_score or (overlap == best_score and is_better_value):
            best_score = overlap
            best_value = value

    return best_value


def _build_artifact_evidence(project_path: str) -> Dict[str, object]:
    changelog = _parse_changelog_evidence(project_path)
    git_history = _parse_git_history_evidence(project_path)
    release_dates = list(changelog.get("release_dates", []))

    return {
        "changelog_issue_dates": changelog.get("issue_dates", {}),
        "changelog_entries": changelog.get("entries", []),
        "git_issue_dates": git_history.get("issue_dates", {}),
        "git_commits": git_history.get("commits", []),
        "release_dates": release_dates,
        "latest_release_date": max(release_dates) if release_dates else None,
        "release_cadence_days": _estimate_release_cadence_days(release_dates),
    }


def _normalize_issue_url(url: str, repository: str, issue_number: int) -> str:
    text = (url or "").strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if repository:
        return f"https://github.com/{repository}/issues/{issue_number}"
    return text


def _clean_status(text: str) -> str:
    cleaned = re.sub(r"[*`_]", "", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _clean_bullet_text(text: str) -> str:
    return _clean_status(re.sub(r"^[-*]\s+", "", text or "").strip())


def _status_is_complete(status: Optional[str]) -> bool:
    normalized = (status or "").lower()
    return "complete" in normalized or "done" in normalized or "released" in normalized


def _humanize_feature_slug(text: str) -> str:
    humanized = re.sub(r"[_-]+", " ", text or "").strip()
    humanized = re.sub(r"\s+", " ", humanized)
    if not humanized:
        return "Untitled issue"
    return humanized[0].upper() + humanized[1:]


def _infer_story_profile(title: str) -> Dict[str, object]:
    normalized = (title or "").lower()
    score = 1

    if "epic" in normalized:
        score += 3

    medium_keywords = [
        "feature",
        "support",
        "crud",
        "dashboard",
        "player",
        "management",
        "admin",
        "integration",
        "portal",
        "automation",
        "versioning",
        "bulk import",
        "bulk ingestion",
        "deep linking",
        "monitoring",
        "logging",
        "pipeline",
        "audio",
        "video",
        "auth",
        "sync",
        "ui",
        "ux",
        "mobile",
        "web",
        "backend",
        "android",
        "ios",
        "migration",
        "infrastructure",
        "architecture",
        "observability",
    ]
    high_keywords = [
        "global",
        "navigator",
        "rag",
        "multi-module",
        "modularization",
        "healthkit",
        "spatial audio",
        "unified",
        "premium",
        "platform",
        "ci/cd",
    ]
    low_keywords = [
        "bug",
        "preflight",
        "follow-up",
        "setup",
        "research",
        "refinement",
        "timestamp",
        "quote",
        "tag",
        "theme",
    ]

    if any(keyword in normalized for keyword in medium_keywords):
        score += 1
    if any(keyword in normalized for keyword in high_keywords):
        score += 1
    if any(keyword in normalized for keyword in low_keywords):
        score -= 1
    if len(normalized) > 70:
        score += 1

    score = max(1, min(score, 6))
    if score <= 1:
        return {"estimate_points": 1, "estimated_mandays": 1.0, "effort_level": "Low"}
    if score == 2:
        return {"estimate_points": 2, "estimated_mandays": 2.0, "effort_level": "Low"}
    if score == 3:
        return {"estimate_points": 3, "estimated_mandays": 3.0, "effort_level": "Medium"}
    if score == 4:
        return {"estimate_points": 5, "estimated_mandays": 5.0, "effort_level": "Medium"}
    if score == 5:
        return {"estimate_points": 8, "estimated_mandays": 8.0, "effort_level": "High"}
    return {"estimate_points": 13, "estimated_mandays": 13.0, "effort_level": "High"}


def apply_heuristic_defaults(record: IssueMetricsRecord) -> IssueMetricsRecord:
    defaults = _infer_story_profile(record.issue_title)

    if record.estimate_points is None:
        record.estimate_points = int(defaults["estimate_points"])
    if record.estimated_mandays is None:
        record.estimated_mandays = float(defaults["estimated_mandays"])
    if record.effort_level is None:
        record.effort_level = str(defaults["effort_level"])
    if record.actual_mandays is None:
        if _status_is_complete(record.issue_status):
            record.actual_mandays = float(record.estimated_mandays or 0.0)
        else:
            record.actual_mandays = 0.0
    return record


def apply_artifact_defaults(
    record: IssueMetricsRecord, evidence: Dict[str, object]
) -> IssueMetricsRecord:
    changelog_issue_dates = evidence.get("changelog_issue_dates", {})
    git_issue_dates = evidence.get("git_issue_dates", {})
    changelog_entries = evidence.get("changelog_entries", [])
    git_commits = evidence.get("git_commits", [])
    latest_release_date = evidence.get("latest_release_date")
    cadence_days = int(evidence.get("release_cadence_days") or 7)

    explicit_release_date = changelog_issue_dates.get(record.issue_number)
    fuzzy_release_date = None
    if _status_is_complete(record.issue_status):
        fuzzy_release_date = _best_fuzzy_date_match(
            record.issue_title,
            changelog_entries,
            minimum_overlap=2,
        )
    release_date = explicit_release_date or fuzzy_release_date

    completion_date = git_issue_dates.get(record.issue_number)
    if completion_date is None and _status_is_complete(record.issue_status):
        completion_date = _best_fuzzy_date_match(
            record.issue_title,
            git_commits,
            minimum_overlap=2,
        )

    if record.actual_completion_date in (None, "") and _status_is_complete(record.issue_status):
        if completion_date:
            record.actual_completion_date = str(completion_date)
        elif release_date:
            record.actual_completion_date = _date_to_completion_anchor(release_date)

    if record.due_date not in (None, ""):
        return record

    if explicit_release_date:
        record.due_date = _date_to_end_of_day(explicit_release_date)
        return record

    if _status_is_complete(record.issue_status):
        if release_date:
            record.due_date = _date_to_end_of_day(release_date)
            return record
        if record.actual_completion_date:
            try:
                actual_dt = datetime.fromisoformat(record.actual_completion_date)
                record.due_date = _date_to_end_of_day(actual_dt.date())
                return record
            except ValueError:
                pass
        if latest_release_date:
            record.due_date = _date_to_end_of_day(latest_release_date)
        return record

    if latest_release_date:
        estimate_days = record.estimated_mandays or 0.0
        projected_days = max(cadence_days, int(round(estimate_days)) or 1)
        record.due_date = _date_to_end_of_day(
            latest_release_date + timedelta(days=projected_days)
        )

    return record


def _maybe_parse_metric_line(record: IssueMetricsRecord, line: str) -> None:
    text = line.strip()
    if not text:
        return

    patterns = [
        ("estimate_points", r"(?:estimate points?|story points?|points?)\s*[:=-]\s*(\d+)"),
        (
            "estimated_mandays",
            r"(?:estimated mandays?|estimated man-?days?|mandays?)\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)",
        ),
        (
            "actual_mandays",
            r"(?:actual mandays?|actual man-?days?)\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?)",
        ),
        (
            "actual_completion_date",
            r"(?:actual completion(?: date/time| date)?|completed at|done at)\s*[:=-]\s*(.+)$",
        ),
        ("due_date", r"(?:due date/time|due date|due)\s*[:=-]\s*(.+)$"),
        ("effort_level", r"(?:effort level|effort)\s*[:=-]\s*(low|medium|high)\b"),
    ]

    for field_name, pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue

        raw_value = match.group(1).strip()
        if field_name == "estimate_points":
            record.estimate_points = int(raw_value)
        elif field_name in ("estimated_mandays", "actual_mandays"):
            setattr(record, field_name, float(raw_value))
        elif field_name in ("due_date", "actual_completion_date"):
            try:
                setattr(record, field_name, parse_metric_datetime(raw_value))
            except ValueError:
                pass
        elif field_name == "effort_level":
            try:
                record.effort_level = validate_effort_level(raw_value)
            except ValueError:
                pass
        return


def parse_roadmap_issue_metrics(
    project_path: str, project_name: Optional[str], repository: Optional[str]
) -> List[IssueMetricsRecord]:
    roadmap_path = get_roadmap_path(project_path)
    if not roadmap_path:
        return []

    with open(roadmap_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    table_issue_re = re.compile(
        r"^\|\s*\[#?(?P<number>\d+)\]\((?P<url>[^)]*)\)\s*\|\s*(?P<title>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|"
    )
    block_issue_re = re.compile(r"^###\s+Issue\s+#(?P<number>\d+)\s*-\s*(?P<title>.+)$", re.IGNORECASE)
    bullet_issue_re = re.compile(
        r"^-\s+\*\*#(?P<number>\d+)\s+(?P<title>.+?)\*\*(?:\s*\((?P<suffix>[^)]*)\))?\s*$"
    )
    github_link_re = re.compile(r"\[#?(?P<number>\d+)\]\((?P<url>https?://[^)]+)\)")
    status_re = re.compile(r"\*\*Status:\*\*\s*(?P<status>.+)$", re.IGNORECASE)
    state_re = re.compile(r"\*\*State:\*\*\s*(?P<status>.+)$", re.IGNORECASE)

    candidates: Dict[str, IssueMetricsRecord] = {}
    current_block: Optional[IssueMetricsRecord] = None

    def _append_current_block() -> None:
        nonlocal current_block
        if current_block:
            candidates[current_block.issue_key] = current_block
            current_block = None

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        table_match = table_issue_re.match(stripped)
        if table_match:
            issue_number = int(table_match.group("number"))
            issue_url = _normalize_issue_url(
                table_match.group("url"), repository, issue_number
            )
            record = IssueMetricsRecord(
                issue_key=issue_key_for(repository or "", issue_number),
                issue_number=issue_number,
                issue_title=table_match.group("title").strip(),
                issue_url=issue_url,
                repository=repository or "",
                project_name=project_name,
                issue_status=_clean_status(table_match.group("status")),
            )
            candidates[record.issue_key] = record
            continue

        block_match = block_issue_re.match(stripped)
        if block_match:
            _append_current_block()
            issue_number = int(block_match.group("number"))
            current_block = IssueMetricsRecord(
                issue_key=issue_key_for(repository or "", issue_number),
                issue_number=issue_number,
                issue_title=block_match.group("title").strip(),
                issue_url=_normalize_issue_url("", repository, issue_number),
                repository=repository or "",
                project_name=project_name,
            )
            continue

        bullet_match = bullet_issue_re.match(stripped)
        if bullet_match:
            _append_current_block()
            issue_number = int(bullet_match.group("number"))
            title = bullet_match.group("title").strip()
            suffix = (bullet_match.group("suffix") or "").strip()
            if suffix:
                title = f"{title} ({suffix})"
            current_block = IssueMetricsRecord(
                issue_key=issue_key_for(repository or "", issue_number),
                issue_number=issue_number,
                issue_title=title,
                issue_url=_normalize_issue_url("", repository, issue_number),
                repository=repository or "",
                project_name=project_name,
            )
            continue

        if current_block is None:
            continue

        link_match = github_link_re.search(stripped)
        if link_match:
            current_block.issue_url = link_match.group("url").strip()

        status_match = status_re.search(stripped) or state_re.search(stripped)
        if status_match:
            current_block.issue_status = _clean_status(status_match.group("status"))
        elif stripped.startswith("- ") and (
            "done" in stripped.lower()
            or "complete" in stripped.lower()
            or "planned" in stripped.lower()
            or "todo" in stripped.lower()
            or "in progress" in stripped.lower()
            or "blocked" in stripped.lower()
        ):
            current_block.issue_status = _clean_bullet_text(stripped)

        _maybe_parse_metric_line(current_block, stripped)

        if stripped.startswith("## ") and not stripped.startswith("### "):
            _append_current_block()

    _append_current_block()
    return list(candidates.values())


def parse_feature_dir_issue_metrics(
    project_path: str, project_name: Optional[str], repository: Optional[str]
) -> List[IssueMetricsRecord]:
    features_root = os.path.join(project_path, "docs", "features")
    if not os.path.isdir(features_root):
        return []

    issue_token_re = re.compile(r"issue-(?P<numbers>\d+(?:-\d+)*)", re.IGNORECASE)
    candidates: Dict[str, IssueMetricsRecord] = {}

    for entry in sorted(os.listdir(features_root)):
        full_path = os.path.join(features_root, entry)
        if not os.path.isdir(full_path):
            continue

        match = issue_token_re.search(entry)
        if not match:
            continue

        numbers = [int(part) for part in match.group("numbers").split("-") if part.isdigit()]
        slug = entry[match.end():].strip(" _-")
        title = _humanize_feature_slug(slug)

        for issue_number in numbers:
            record = IssueMetricsRecord(
                issue_key=issue_key_for(repository or "", issue_number),
                issue_number=issue_number,
                issue_title=title,
                issue_url=_normalize_issue_url("", repository, issue_number),
                repository=repository or "",
                project_name=project_name,
            )
            candidates[record.issue_key] = record

    return list(candidates.values())


def prefill_metrics_from_roadmap(
    project_path: str, project_name: Optional[str], repository: Optional[str]
) -> Dict[str, int]:
    candidates_by_key: Dict[str, IssueMetricsRecord] = {}
    for candidate in parse_roadmap_issue_metrics(project_path, project_name, repository):
        candidates_by_key[candidate.issue_key] = candidate
    for candidate in parse_feature_dir_issue_metrics(project_path, project_name, repository):
        candidates_by_key.setdefault(candidate.issue_key, candidate)

    candidates = list(candidates_by_key.values())
    if not candidates:
        return {"created": 0, "updated": 0}

    evidence = _build_artifact_evidence(project_path)
    store = load_metrics_store(project_path)
    issues = store.setdefault("issues", {})
    created = 0
    updated = 0

    for candidate in candidates:
        candidate = apply_heuristic_defaults(candidate)
        candidate = apply_artifact_defaults(candidate, evidence)
        existing_raw = issues.get(candidate.issue_key)
        if not isinstance(existing_raw, dict):
            issues[candidate.issue_key] = candidate.to_dict()
            created += 1
            continue

        existing = IssueMetricsRecord.from_dict(existing_raw)
        changed = False

        metadata_fields = ("issue_title", "issue_url", "issue_status", "project_name")
        for field_name in metadata_fields:
            candidate_value = getattr(candidate, field_name)
            if candidate_value and getattr(existing, field_name) != candidate_value:
                setattr(existing, field_name, candidate_value)
                changed = True

        metric_fields = (
            "estimate_points",
            "estimated_mandays",
            "actual_mandays",
            "due_date",
            "actual_completion_date",
            "effort_level",
            "notes",
        )
        for field_name in metric_fields:
            existing_value = getattr(existing, field_name)
            candidate_value = getattr(candidate, field_name)
            if existing_value in (None, "") and candidate_value not in (None, ""):
                setattr(existing, field_name, candidate_value)
                changed = True

        if existing.actual_mandays is None:
            if _status_is_complete(existing.issue_status):
                existing.actual_mandays = float(existing.estimated_mandays or 0.0)
            else:
                existing.actual_mandays = 0.0
            changed = True

        if changed:
            existing.updated_at = _now_iso()
            issues[candidate.issue_key] = existing.to_dict()
            updated += 1

    if created or updated:
        save_metrics_store(project_path, store)

    return {"created": created, "updated": updated}
