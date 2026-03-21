import pytest
from datetime import date
from unittest.mock import patch, mock_open
from luma_core.issue_metrics import IssueMetricsRecord
from luma_core.report_generator import generate_report

def create_mock_issue(
    issue_number: int,
    status: str,
    due_date: str = None,
    actual_completion_date: str = None,
    points: int = 2,
    actual_mandays: float = 2.0,
    estimated_mandays: float = 2.0,
    created_at: str = "2026-03-01T10:00:00"
) -> IssueMetricsRecord:
    return IssueMetricsRecord(
        issue_key=f"mock/Repo#{issue_number}",
        issue_number=issue_number,
        issue_title=f"Mock Issue {issue_number}",
        issue_url=f"https://github.com/mock/Repo/issues/{issue_number}",
        repository="mock/Repo",
        project_name="MockProject",
        issue_status=status,
        estimate_points=points,
        estimated_mandays=estimated_mandays,
        actual_mandays=actual_mandays,
        due_date=due_date,
        actual_completion_date=actual_completion_date,
        effort_level="Low",
        created_at=created_at,
    )

@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_velocity_summary_counts_completed_in_period(mock_get_roadmap_path, mock_list_metrics):
    mock_get_roadmap_path.return_value = None
    mock_list_metrics.return_value = [
        create_mock_issue(1, "✅ Complete", actual_completion_date="2026-03-20T10:00:00", points=3),
        create_mock_issue(2, "✅ Complete", actual_completion_date="2026-03-18T10:00:00", points=5),
        create_mock_issue(3, "✅ Complete", actual_completion_date="2026-03-10T10:00:00", points=2), # Previous period
        create_mock_issue(4, "🔲 Todo", due_date="2026-03-25T10:00:00")
    ]
    
    # Weekly report for the week of 2026-03-21 (ISO week includes 2026-03-16 to 2026-03-22)
    report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    assert "Velocity Summary" in report
    assert "**Issues completed in this period:** 2" in report
    assert "**Total points:** 8" in report

@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_ontime_delivery_rate_calculation(mock_get_roadmap_path, mock_list_metrics):
    mock_get_roadmap_path.return_value = None
    mock_list_metrics.return_value = [
        create_mock_issue(1, "✅ Complete", due_date="2026-03-19T23:59:59", actual_completion_date="2026-03-18T10:00:00"), # On time
        create_mock_issue(2, "✅ Complete", due_date="2026-03-18T23:59:59", actual_completion_date="2026-03-20T10:00:00"), # Late
    ]
    
    report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    assert "On-time Delivery Rate" in report
    # 1 out of 2 completed issues were on time
    assert "1/2" in report
    assert "50%" in report

@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_overdue_issues_detection(mock_get_roadmap_path, mock_list_metrics):
    mock_get_roadmap_path.return_value = None
    mock_list_metrics.return_value = [
        create_mock_issue(1, "🔲 Todo", due_date="2026-03-15T23:59:59"), # Overdue
        create_mock_issue(2, "⏳ In Progress", due_date="2026-03-20T23:59:59"), # Overdue
        create_mock_issue(3, "🔲 Todo", due_date="2026-04-30T23:59:59") # Not overdue and not upcoming
    ]
    
    report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    assert "Overdue Issues" in report
    assert "Mock Issue 1" in report
    assert "Mock Issue 2" in report
    assert "Mock Issue 3" not in report

@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_upcoming_due_dates_filtering(mock_get_roadmap_path, mock_list_metrics):
    mock_get_roadmap_path.return_value = None
    mock_list_metrics.return_value = [
        create_mock_issue(1, "🔲 Todo", due_date="2026-03-25T23:59:59"), # In next 7 days
        create_mock_issue(2, "🔲 Todo", due_date="2026-04-10T23:59:59"), # Outside 7 days
        create_mock_issue(3, "✅ Complete", due_date="2026-03-24T23:59:59") # Completed, shouldn't be in upcoming
    ]
    
    report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    assert "Upcoming Due Dates" in report
    assert "Mock Issue 1" in report
    assert "Mock Issue 2" not in report
    assert "Mock Issue 3" not in report

@patch("builtins.open", new_callable=mock_open, read_data="""
## Phase 1: Foundation
| # | Issue | Status |
|---|---|---|
| [#1](url) | Something | ✅ Complete |
| [#2](url) | Another | 🔲 Todo |
## Phase 2: Next
| # | Issue | Status |
|---|---|---|
| [#3](url) | Future | 🔲 Todo |
    """)
@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_phase_progress_from_roadmap(mock_get_roadmap_path, mock_list_metrics, mock_file):
    mock_get_roadmap_path.return_value = "/mock/path/ROADMAP.md"
    with patch("os.path.exists", return_value=True):
        report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    assert "Phase Progress" in report
    assert "Phase 1: Foundation" in report
    assert "Phase 2: Next" in report
    assert "1/2" in report # 1 complete out of 2 for Phase 1
    assert "50%" in report # 50% for Phase 1
    assert "0/1" in report # 0 complete out of 1 for Phase 2

@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_empty_metrics_returns_empty_report(mock_get_roadmap_path, mock_list_metrics):
    mock_get_roadmap_path.return_value = None
    mock_list_metrics.return_value = []
    
    report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    assert "Weekly Report" in report
    assert "Velocity Summary" in report
    assert "**Issues completed in this period:** 0" in report

@patch("luma_core.report_generator._fetch_gh_issue_dates")
@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_completed_issues_are_listed_in_report(mock_get_roadmap_path, mock_list_metrics, mock_gh_dates):
    mock_get_roadmap_path.return_value = None
    mock_list_metrics.return_value = [
        create_mock_issue(10, "✅ Complete",
            actual_completion_date="2026-03-18T10:00:00", points=3,
            due_date="2026-03-20T23:59:59", created_at="2026-03-10T08:00:00"),
        create_mock_issue(11, "✅ Complete",
            actual_completion_date="2026-03-20T14:00:00", points=5,
            due_date="2026-03-25T23:59:59", created_at="2026-03-12T09:00:00"),
        create_mock_issue(12, "🔲 Todo", due_date="2026-03-25T10:00:00")
    ]
    mock_gh_dates.return_value = {
        10: {"createdAt": "2026-03-05T08:00:00Z", "closedAt": "2026-03-18T14:30:00Z"},
        11: {"createdAt": "2026-03-08T09:00:00Z", "closedAt": "2026-03-20T16:00:00Z"},
    }
    
    report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    # Should have a "Completed Issues" section listing each done issue
    assert "## Completed Issues" in report
    assert "#10" in report
    assert "Mock Issue 10" in report
    assert "#11" in report
    assert "Mock Issue 11" in report
    # Should show dates from GitHub (Created + Completed) and metrics (Due)
    completed_section = report.split("## Completed Issues")[1].split("##")[0]
    assert "Created:" in completed_section
    assert "2026-03-05" in completed_section  # GH created date of #10
    assert "Due:" in completed_section
    assert "Completed:" in completed_section
    assert "2026-03-18" in completed_section  # GH closedAt of #10 (not fuzzy 03-17)
    assert "2026-03-20" in completed_section  # GH closedAt of #11
    # Not-completed issue should NOT appear in that section
    assert "Mock Issue 12" not in completed_section

@patch("luma_core.report_generator.list_issue_metrics")
@patch("luma_core.report_generator.get_roadmap_path")
def test_human_readable_summary_section(mock_get_roadmap_path, mock_list_metrics):
    mock_get_roadmap_path.return_value = None
    mock_list_metrics.return_value = [
        create_mock_issue(1, "✅ Complete", actual_completion_date="2026-03-18T10:00:00", points=3),
        create_mock_issue(2, "✅ Complete", actual_completion_date="2026-03-20T14:00:00", points=5),
        create_mock_issue(3, "🔲 Todo", due_date="2026-03-15T10:00:00"),  # overdue
    ]
    
    report = generate_report("/mock/path", period="weekly", reference_date=date(2026, 3, 21))
    
    # Should have a summary section at the top with human-readable text
    assert "## Summary" in report
    # Summary should mention how many issues were completed
    assert "2" in report.split("## Summary")[1].split("##")[0]
