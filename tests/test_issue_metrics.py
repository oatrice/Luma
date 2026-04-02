from dataclasses import asdict
from typing import Dict, Any
import os
import subprocess
from unittest.mock import patch

from luma_core.issue_metrics import (
    IssueMetricsRecord,
    _fetch_github_issue_activity_hint,
    apply_artifact_defaults,
    apply_heuristic_defaults,
    apply_planning_defaults,
    apply_pre_pr_defaults,
    format_metric_datetime,
    get_issue_metrics,
    list_issue_metrics,
    parse_metric_datetime,
    prefill_metrics_from_roadmap,
    save_issue_metrics,
    suggest_post_story_point,
    sync_github_metrics_for_project,
)


def test_issue_metrics_start_datetime_defaults_to_none():
    """start_datetime ต้อง default เป็น None เมื่อไม่ได้ระบุ"""
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#1",
        issue_number=1,
        issue_title="Test",
        issue_url="https://github.com/oatrice/Luma/issues/1",
        repository="oatrice/Luma",
    )
    assert record.start_datetime is None


def test_issue_metrics_start_datetime_roundtrip(tmp_path):
    """start_datetime ต้อง save/load ได้ถูกต้องและ normalize เป็น ISO format"""
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#20",
        issue_number=20,
        issue_title="Start datetime test",
        issue_url="https://github.com/oatrice/Luma/issues/20",
        repository="oatrice/Luma",
        start_datetime="2026-03-26 09:00",
    )

    saved = save_issue_metrics(str(tmp_path), record)
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 20)

    assert saved.start_datetime == "2026-03-26T09:00:00"
    assert loaded is not None
    assert loaded.start_datetime == "2026-03-26T09:00:00"


def test_issue_metrics_start_datetime_from_dict_backward_compat():
    """from_dict ต้องทำงานได้ถึงแม้ไม่มี start_datetime key (backward compat)"""
    data = {
        "issue_key": "oatrice/Luma#21",
        "issue_number": 21,
        "issue_title": "Old record",
        "issue_url": "https://github.com/oatrice/Luma/issues/21",
        "repository": "oatrice/Luma",
    }
    record = IssueMetricsRecord.from_dict(data)
    assert record.start_datetime is None


def test_issue_metrics_start_datetime_parsed_from_roadmap_body(tmp_path):
    """parse metric line ต้อง parse 'start datetime: ...' จาก roadmap body ได้"""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "### Issue #22 - Start datetime parsing test\n"
        "- **Status:** 🔵 In Progress\n"
        "- Start Datetime: 2026-03-25 08:30\n",
        encoding="utf-8",
    )

    prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 22)

    assert loaded is not None
    assert loaded.start_datetime == "2026-03-25T08:30:00"


def test_apply_planning_defaults_sets_estimates_and_start_without_actuals():
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#23",
        issue_number=23,
        issue_title="Feature planning sync",
        issue_url="https://github.com/oatrice/Luma/issues/23",
        repository="oatrice/Luma",
        issue_status="🟡 In Progress",
    )

    changed = apply_planning_defaults(record, started_at="2026-04-02T10:30:00")

    assert changed is True
    assert record.estimate_points is not None
    assert record.estimated_mandays is not None
    assert record.effort_level in ("Low", "Medium", "High")
    assert record.start_datetime == "2026-04-02T10:30:00"
    assert record.actual_completion_date is None
    assert record.actual_mandays is None


def test_apply_pre_pr_defaults_sets_actuals_before_issue_is_closed():
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#24",
        issue_number=24,
        issue_title="Feature ready for PR",
        issue_url="https://github.com/oatrice/Luma/issues/24",
        repository="oatrice/Luma",
        issue_status="🟢 Ready",
        estimate_points=3,
        estimated_mandays=1.5,
        effort_level="Medium",
        start_datetime="2026-04-01T09:00:00",
    )

    changed = apply_pre_pr_defaults(record, completed_at="2026-04-02T21:00:00")

    assert changed is True
    assert record.actual_completion_date == "2026-04-02T21:00:00"
    assert record.actual_mandays == 1.5
    assert record.issue_status == "🟢 Ready"


def test_issue_metrics_roundtrip_with_zero_values(tmp_path):
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#9",
        issue_number=9,
        issue_title="Track issue metrics",
        issue_url="https://github.com/oatrice/Luma/issues/9",
        repository="oatrice/Luma",
        project_name="Luma",
        estimate_points=0,
        estimated_mandays=0,
        actual_mandays=0,
        due_date="2026-03-19 14:30",
        actual_completion_date="2026-03-20T08:15",
        effort_level="Medium",
        notes="Initial tracking record",
    )

    saved = save_issue_metrics(str(tmp_path), record)
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 9)

    assert saved.updated_at
    assert loaded is not None
    assert loaded.estimate_points == 0
    assert loaded.estimated_mandays == 0.0
    assert loaded.actual_mandays == 0.0
    assert loaded.due_date == "2026-03-19T14:30:00"
    assert loaded.actual_completion_date == "2026-03-20T08:15:00"
    assert loaded.effort_level == "Medium"
    assert format_metric_datetime(loaded.due_date) == "2026-03-19 14:30:00"


def test_issue_metrics_post_story_point_roundtrip_with_half_step(tmp_path):
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#29",
        issue_number=29,
        issue_title="Track post story point",
        issue_url="https://github.com/oatrice/Luma/issues/29",
        repository="oatrice/Luma",
        estimate_points=2,
        post_story_point=0.5,
    )

    save_issue_metrics(str(tmp_path), record)
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 29)

    assert loaded is not None
    assert loaded.post_story_point == 0.5


def test_issue_metrics_reject_invalid_post_story_point_value(tmp_path):
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#30",
        issue_number=30,
        issue_title="Bad post story point",
        issue_url="https://github.com/oatrice/Luma/issues/30",
        repository="oatrice/Luma",
        post_story_point=4,
    )

    try:
        save_issue_metrics(str(tmp_path), record)
    except ValueError as exc:
        assert "Post Story Point" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid post story point")


def test_calculate_actual_mandays_from_dates(tmp_path):
    record = IssueMetricsRecord(
        issue_key="test#1",
        issue_number=1,
        issue_title="Test calculating actual mandays",
        issue_url="https://github.com/test/issues/1",
        repository="test",
        issue_status="Complete",
        estimated_mandays=5.0,
        start_datetime="2026-03-24T10:00:00",
        actual_completion_date="2026-03-26T15:00:00"
    )
    
    # 2026-03-24 10:00 to 2026-03-26 15:00 is 2 days and 5 hours = 53 hours. 53 / 24 = 2.208
    # With nearest half day, it should be 2.0 or 2.5 depending on rounding.
    # We round to nearest half day: round(2.208 * 2) / 2 = 4/2 = 2.0
    record = apply_heuristic_defaults(record)
    assert record.actual_mandays == 2.0
    
    # What if it's the same day?
    record_same_day = dict(asdict(record))
    record_same_day["start_datetime"] = "2026-03-24T10:00:00"
    record_same_day["actual_completion_date"] = "2026-03-24T11:00:00"
    record_same_day["actual_mandays"] = None
    
    r2 = apply_heuristic_defaults(IssueMetricsRecord(**record_same_day))
    assert r2.actual_mandays == 0.5  # minimum half day


def test_issue_metrics_reject_invalid_effort_level(tmp_path):
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#10",
        issue_number=10,
        issue_title="Bad effort",
        issue_url="https://github.com/oatrice/Luma/issues/10",
        repository="oatrice/Luma",
        effort_level="Very High",
    )

    try:
        save_issue_metrics(str(tmp_path), record)
    except ValueError as exc:
        assert "Effort Level" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid effort level")


def test_issue_metrics_list_sorts_newest_first(tmp_path):
    older = IssueMetricsRecord(
        issue_key="oatrice/Luma#1",
        issue_number=1,
        issue_title="Older",
        issue_url="https://github.com/oatrice/Luma/issues/1",
        repository="oatrice/Luma",
        updated_at="2026-03-19T10:00:00",
    )
    newer = IssueMetricsRecord(
        issue_key="oatrice/Luma#2",
        issue_number=2,
        issue_title="Newer",
        issue_url="https://github.com/oatrice/Luma/issues/2",
        repository="oatrice/Luma",
        updated_at="2026-03-19T11:00:00",
    )

    save_issue_metrics(str(tmp_path), older)
    save_issue_metrics(str(tmp_path), newer)

    records = list_issue_metrics(str(tmp_path))
    assert [record.issue_number for record in records] == [2, 1]


def test_parse_metric_datetime_requires_time_component():
    try:
        parse_metric_datetime("2026-03-19")
    except ValueError as exc:
        assert "Use date/time format" in str(exc)
    else:
        raise AssertionError("Expected ValueError for date-only input")


def test_prefill_metrics_from_roadmap_merges_without_overwriting_manual_values(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "### Issue #33 - Prefilled issue\n"
        "- **Status:** 🟢 **Ready**\n"
        "- Estimate Points: 5\n"
        "- Estimated Mandays: 2.5\n"
        "- Due Date: 2026-03-21 09:30\n",
        encoding="utf-8",
    )

    save_issue_metrics(
        str(tmp_path),
        IssueMetricsRecord(
            issue_key="oatrice/Luma#33",
            issue_number=33,
            issue_title="Old title",
            issue_url="https://github.com/oatrice/Luma/issues/33",
            repository="oatrice/Luma",
            actual_mandays=7.0,
        ),
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 33)

    assert result["updated"] == 1
    assert loaded is not None
    assert loaded.issue_title == "Prefilled issue"
    assert loaded.issue_status == "🟢 Ready"
    assert loaded.estimate_points == 5
    assert loaded.estimated_mandays == 2.5
    assert loaded.due_date == "2026-03-21T09:30:00"
    assert loaded.actual_mandays == 7.0


def test_prefill_metrics_from_roadmap_reads_issue_table_rows(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "| ID | Title | Status |\n"
        "|---|---|---|\n"
        "| [#12](#12) | Table issue | ✅ Complete |\n",
        encoding="utf-8",
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 12)

    assert result["created"] == 1
    assert loaded is not None
    assert loaded.issue_title == "Table issue"
    assert loaded.issue_status == "✅ Complete"
    assert loaded.issue_url == "https://github.com/oatrice/Luma/issues/12"
    assert loaded.estimate_points is not None
    assert loaded.estimated_mandays is not None
    assert loaded.actual_mandays == loaded.estimated_mandays
    assert loaded.effort_level in ("Low", "Medium", "High")


def test_prefill_metrics_from_roadmap_assigns_zero_actuals_for_todo_items(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "| ID | Title | Status |\n"
        "|---|---|---|\n"
        "| [#101](#101) | [Feature] Tech Polish: Mindful haptics & HealthKit integration | 🔲 Todo |\n",
        encoding="utf-8",
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 101)

    assert result["created"] == 1
    assert loaded is not None
    assert loaded.estimate_points is not None
    assert loaded.estimated_mandays is not None
    assert loaded.actual_mandays == 0.0
    assert loaded.effort_level in ("Low", "Medium", "High")


def _init_git_repo_with_commit(tmp_path, subject, commit_date):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.name", "Codex Tests"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "codex-tests@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    (tmp_path / "README.md").write_text("# test repo\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = commit_date
    env["GIT_COMMITTER_DATE"] = commit_date
    subprocess.run(
        ["git", "commit", "-m", subject],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _append_git_commit(tmp_path, subject, commit_date, filename="README.md"):
    path = tmp_path / filename
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + f"\n{subject}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", filename],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = commit_date
    env["GIT_COMMITTER_DATE"] = commit_date
    subprocess.run(
        ["git", "commit", "-m", subject],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def test_suggest_post_story_point_uses_git_history_for_issue_number(tmp_path):
    _init_git_repo_with_commit(
        tmp_path,
        "chore: init repo",
        "2026-03-10T08:00:00+07:00",
    )
    _append_git_commit(
        tmp_path,
        "feat: start issue #50 implementation",
        "2026-03-11T08:00:00+07:00",
    )
    _append_git_commit(
        tmp_path,
        "refactor: improve issue #50 flow",
        "2026-03-12T08:00:00+07:00",
    )
    _append_git_commit(
        tmp_path,
        "test: cover issue #50 edge cases",
        "2026-03-13T08:00:00+07:00",
    )

    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#50",
        issue_number=50,
        issue_title="Post-story-point suggestion",
        issue_url="https://github.com/oatrice/Luma/issues/50",
        repository="oatrice/Luma",
    )

    assert suggest_post_story_point(str(tmp_path), record) == 3.0


@patch("luma_core.issue_metrics.subprocess.run")
def test_fetch_github_issue_activity_hint_sets_timeout(mock_run):
    mock_run.return_value.stdout = '{"comments": []}'

    hint = _fetch_github_issue_activity_hint("/tmp/project", "oatrice/Luma", 20)

    assert hint == 0
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs["timeout"] == 5


def test_prefill_metrics_from_roadmap_uses_git_history_and_changelog_dates(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "| ID | Title | Status |\n"
        "|---|---|---|\n"
        "| [#111](#111) | [Preflight] Media Source Policy + Content Fields (Audio/Video) | ✅ Complete |\n",
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [0.19.0] - 2026-03-19\n\n"
        "### Added\n"
        "- [Docs] Added preflight analysis for media source policy (issue #111)\n",
        encoding="utf-8",
    )
    _init_git_repo_with_commit(
        tmp_path,
        "docs: add preflight analysis for media source policy (#111)",
        "2026-03-19T08:57:18+07:00",
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 111)

    assert result["created"] == 1
    assert loaded is not None
    assert loaded.actual_completion_date == "2026-03-19T08:57:18"
    assert loaded.due_date == "2026-03-19T23:59:59"


def test_prefill_metrics_from_roadmap_projects_due_date_from_latest_release(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "| ID | Title | Status |\n"
        "|---|---|---|\n"
        "| [#101](#101) | [Feature] Tech Polish: Mindful haptics & HealthKit integration | 🔲 Todo |\n",
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [0.18.0] - 2026-03-18\n\n"
        "- Previous release notes\n\n"
        "## [0.19.0] - 2026-03-19\n\n"
        "- Current release notes\n",
        encoding="utf-8",
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 101)

    assert result["created"] == 1
    assert loaded is not None
    assert loaded.estimated_mandays == 1.5
    assert loaded.actual_completion_date is None
    assert loaded.due_date == "2026-03-21T23:59:59"


def test_prefill_metrics_from_roadmap_can_fuzzy_match_completion_commit(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "| ID | Title | Status |\n"
        "|---|---|---|\n"
        "| [#65](#65) | Automate Issue to Project Board Workflow | ✅ Complete |\n",
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [0.11.0] - 2026-03-05\n\n"
        "- Added a GitHub Actions workflow to automatically add new issues to the project board.\n",
        encoding="utf-8",
    )
    _init_git_repo_with_commit(
        tmp_path,
        "Add GitHub workflow to automatically add new issues to the project board",
        "2026-03-05T09:15:00+07:00",
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 65)

    assert result["created"] == 1
    assert loaded is not None
    assert loaded.actual_completion_date == "2026-03-05T09:15:00"
    assert loaded.due_date == "2026-03-05T23:59:59"


def test_prefill_metrics_from_roadmap_reads_bullet_issue_blocks(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ROADMAP.md").write_text(
        "# Roadmap\n\n"
        "## Current\n\n"
        "- **#46 Draft Transaction Review (Android)**\n"
        "    - **Status:** 📝 Planned\n"
        "- **#68 Report Filters**\n"
        "    - ✅ **Done** (v1.8.0)\n",
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [1.8.0] - 2026-03-10\n\n"
        "- Released report filters\n",
        encoding="utf-8",
    )
    _init_git_repo_with_commit(
        tmp_path,
        "feat: report filters (#68)",
        "2026-03-09T10:30:00+07:00",
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "JarWise", "oatrice/JarWise-Root")
    planned = get_issue_metrics(str(tmp_path), "oatrice/JarWise-Root", 46)
    done = get_issue_metrics(str(tmp_path), "oatrice/JarWise-Root", 68)

    assert result["created"] == 2
    assert planned is not None
    assert planned.issue_title == "Draft Transaction Review (Android)"
    assert "Planned" in (planned.issue_status or "")
    assert planned.actual_completion_date is None
    assert planned.due_date == "2026-03-17T23:59:59"
    assert done is not None
    assert "Done" in (done.issue_status or "")
    assert done.actual_completion_date == "2026-03-09T10:30:00"


def test_prefill_metrics_from_feature_dirs_without_roadmap(tmp_path):
    features_dir = tmp_path / "docs" / "features"
    features_dir.mkdir(parents=True)
    (features_dir / "8_issue-9_feature-tracking-estimate-points-mandays-and-effort").mkdir()
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [1.4.1] - 2026-03-19\n\n"
        "- Maintenance release\n",
        encoding="utf-8",
    )

    result = prefill_metrics_from_roadmap(str(tmp_path), "Luma", "oatrice/Luma")
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 9)

    assert result["created"] == 1
    assert loaded is not None
    assert loaded.issue_title == "Feature tracking estimate points mandays and effort"
    assert loaded.due_date == "2026-03-26T23:59:59"


def test_sync_github_metrics_for_project(tmp_path):
    from unittest.mock import patch, MagicMock
    
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#123",
        issue_number=123,
        issue_title="Testing Github Sync",
        issue_url="https://github.com/oatrice/Luma/issues/123",
        repository="oatrice/Luma",
        start_datetime="2026-03-24T10:00:00",
        actual_completion_date="2026-03-25T15:00:00",
        estimated_mandays=1.5
    )
    save_issue_metrics(str(tmp_path), record)

    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = '[{"number": 123, "createdAt": "2026-03-23T08:00:00Z", "closedAt": "2026-03-26T10:00:00Z"}]'
        mock_run.return_value = mock_process

        result = sync_github_metrics_for_project(str(tmp_path), "Luma", "oatrice/Luma")

    assert result["updated"] == 1
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 123)
    assert loaded.gh_closed_at == "2026-03-26T10:00:00Z"
    assert loaded.created_at == "2026-03-23T08:00:00Z"
    assert loaded.gh_mandays == 2.0  # 24th 10:00 to 26th 10:00 = exactly 48 hours = 2 days


def test_sync_github_metrics_fixes_paradox(tmp_path):
    from unittest.mock import patch, MagicMock
    
    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#124",
        issue_number=124,
        issue_title="Testing Paradox Fix",
        issue_url="https://github.com/oatrice/Luma/issues/124",
        repository="oatrice/Luma",
        start_datetime="2026-03-26T00:00:00",  # Paradox: started after it finished locally
        actual_completion_date="2026-03-25T15:00:00",
        estimated_mandays=2.0
    )
    save_issue_metrics(str(tmp_path), record)

    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = '[{"number": 124, "createdAt": "2026-03-23T08:00:00Z", "closedAt": "2026-03-27T15:00:00Z"}]'
        mock_run.return_value = mock_process

        result = sync_github_metrics_for_project(str(tmp_path), "Luma", "oatrice/Luma")

    assert result["updated"] == 1
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 124)
    assert loaded.gh_closed_at == "2026-03-27T15:00:00Z"
    
    # Due to paradox (start_datetime 26th > actual_completion 25th), 
    # it should backfill start_datetime by subtracting estimated_mandays from actual_completion_date
    # 25th 15:00 - 48 hours = 23rd 15:00
    assert loaded.start_datetime == "2026-03-23T15:00:00"
    assert loaded.actual_completion_date == "2026-03-27T15:00:00"
    
    # gh_mandays = 23rd 15:00 to 27th 15:00 = 4 days
    assert loaded.gh_mandays == 4.0
    assert loaded.actual_mandays == 4.0


def test_sync_github_metrics_clears_stale_closed_fields_for_open_issue(tmp_path):
    from unittest.mock import patch, MagicMock

    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#125",
        issue_number=125,
        issue_title="Open issue with stale closed fields",
        issue_url="https://github.com/oatrice/Luma/issues/125",
        repository="oatrice/Luma",
        issue_status="✅ Done",
        start_datetime="2026-03-24T10:00:00",
        actual_mandays=2.0,
        actual_completion_date="2026-03-25T15:00:00",
        gh_closed_at="2026-03-25T15:00:00Z",
        gh_mandays=1.5,
        estimated_mandays=1.5,
    )
    save_issue_metrics(str(tmp_path), record)

    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = (
            '[{"number": 125, "createdAt": "2026-03-23T08:00:00Z", "closedAt": null, '
            '"projectItems": [{"status": {"name": "Ready"}}], "stateReason": ""}]'
        )
        mock_run.return_value = mock_process

        result = sync_github_metrics_for_project(str(tmp_path), "Luma", "oatrice/Luma")

    assert result["updated"] == 1
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 125)
    assert loaded.created_at == "2026-03-23T08:00:00Z"
    assert loaded.issue_status == "🟢 Ready"
    assert loaded.gh_closed_at is None
    assert loaded.actual_completion_date is None
    assert loaded.gh_mandays is None
    assert loaded.actual_mandays == 0.0


def test_sync_github_metrics_keeps_post_story_point_for_reopened_issue(tmp_path):
    from unittest.mock import patch, MagicMock

    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#126",
        issue_number=126,
        issue_title="Open issue keeps post point",
        issue_url="https://github.com/oatrice/Luma/issues/126",
        repository="oatrice/Luma",
        issue_status="✅ Done",
        estimate_points=3,
        post_story_point=5,
        actual_completion_date="2026-03-25T15:00:00",
        gh_closed_at="2026-03-25T15:00:00Z",
    )
    save_issue_metrics(str(tmp_path), record)

    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = (
            '[{"number": 126, "createdAt": "2026-03-23T08:00:00Z", "closedAt": null, '
            '"projectItems": [{"status": {"name": "Ready"}}], "stateReason": ""}]'
        )
        mock_run.return_value = mock_process

        sync_github_metrics_for_project(str(tmp_path), "Luma", "oatrice/Luma")

    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 126)
    assert loaded is not None
    assert loaded.post_story_point == 5


def test_sync_github_metrics_keeps_local_pre_pr_completion_for_open_issue(tmp_path):
    from unittest.mock import patch, MagicMock

    record = IssueMetricsRecord(
        issue_key="oatrice/Luma#127",
        issue_number=127,
        issue_title="Open issue with local pre-PR metrics",
        issue_url="https://github.com/oatrice/Luma/issues/127",
        repository="oatrice/Luma",
        issue_status="🟢 Ready",
        start_datetime="2026-03-24T10:00:00",
        actual_mandays=2.0,
        actual_completion_date="2026-03-25T15:00:00",
        estimated_mandays=1.5,
    )
    save_issue_metrics(str(tmp_path), record)

    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = (
            '[{"number": 127, "createdAt": "2026-03-23T08:00:00Z", "closedAt": null, '
            '"projectItems": [{"status": {"name": "Ready"}}], "stateReason": ""}]'
        )
        mock_run.return_value = mock_process

        result = sync_github_metrics_for_project(str(tmp_path), "Luma", "oatrice/Luma")

    assert result["updated"] == 1
    loaded = get_issue_metrics(str(tmp_path), "oatrice/Luma", 127)
    assert loaded is not None
    assert loaded.created_at == "2026-03-23T08:00:00Z"
    assert loaded.issue_status == "🟢 Ready"
    assert loaded.actual_completion_date == "2026-03-25T15:00:00"
    assert loaded.actual_mandays == 2.0


def test_sync_github_metrics_maps_backlog_for_open_issue_with_stale_completion(tmp_path):
    from unittest.mock import patch, MagicMock

    record = IssueMetricsRecord(
        issue_key="oatrice/JarWise-Root#86",
        issue_number=86,
        issue_title="Select date range export data to Excel/CSV",
        issue_url="https://github.com/oatrice/JarWise-Root/issues/86",
        repository="oatrice/JarWise-Root",
        issue_status="✅ Done",
        start_datetime="2026-02-12T13:00:33",
        actual_mandays=1.0,
        actual_completion_date="2026-03-28T15:14:14",
        gh_closed_at="2026-03-28T15:14:14Z",
        gh_mandays=44.5,
        estimated_mandays=0.5,
    )
    save_issue_metrics(str(tmp_path), record)

    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = (
            '[{"number": 86, "createdAt": "2026-02-12T13:00:30Z", "closedAt": null, '
            '"projectItems": [{"status": {"name": "Backlog"}}], "stateReason": ""}]'
        )
        mock_run.return_value = mock_process

        result = sync_github_metrics_for_project(str(tmp_path), "JarWise", "oatrice/JarWise-Root")

    assert result["updated"] == 1
    loaded = get_issue_metrics(str(tmp_path), "oatrice/JarWise-Root", 86)
    assert loaded.created_at == "2026-02-12T13:00:30Z"
    assert loaded.issue_status == "🔵 Backlog"
    assert loaded.gh_closed_at is None
    assert loaded.actual_completion_date is None
    assert loaded.gh_mandays is None
    assert loaded.actual_mandays == 0.0
