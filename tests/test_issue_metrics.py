from luma_core.issue_metrics import (
    IssueMetricsRecord,
    format_metric_datetime,
    get_issue_metrics,
    list_issue_metrics,
    parse_metric_datetime,
    save_issue_metrics,
)


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
