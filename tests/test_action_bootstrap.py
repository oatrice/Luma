import pytest
from unittest.mock import MagicMock, patch
from luma_core.state_manager import LumaState, WorkflowPhase
from luma_core.actions.issue_actions import bootstrap_issue
from luma_core.actions.utils import KanbanCard

@pytest.fixture
def mock_state():
    state = LumaState()
    state.phase = WorkflowPhase.IDLE
    return state

@pytest.fixture
def mock_project():
    return {
        "name": "Test Project",
        "path": "/tmp/test-project",
        "kanban_number": 1,
        "repo": "oatrice/Luma",
        "kanban_id": "test_kanban"
    }

@patch("luma_core.actions.issue_actions.fetch_kanban_cards")
@patch("luma_core.actions.utils.transition_to")
@patch("subprocess.run")
def test_bootstrap_issue_success(mock_run, mock_transition, mock_fetch, mock_state, mock_project):
    # Setup mock data
    card1 = KanbanCard(
        issue_number=40,
        title="Test Issue 40",
        url="http://github.com/oatrice/Luma/issues/40",
        body="Description 40",
        status="Ready",
        item_id="item40",
        repository="oatrice/Luma"
    )
    mock_fetch.return_value = [card1]
    mock_transition.return_value = (True, "Success")
    mock_run.return_value = MagicMock(returncode=0)

    # Execute
    result = bootstrap_issue(mock_state, mock_project, issue_numbers=[40])

    # Assertions
    assert result is True
    assert len(mock_state.active_issues) > 0
    assert mock_state.active_issues[0].number == 40
    mock_transition.assert_called()
    # Check if git branch was created
    mock_run.assert_any_call(
        ["git", "checkout", "-b", pytest.any],
        cwd=mock_project["path"],
        capture_output=True,
        text=True
    )

@patch("luma_core.actions.issue_actions.fetch_kanban_cards")
def test_bootstrap_issue_not_found(mock_fetch, mock_state, mock_project):
    mock_fetch.return_value = []
    
    # Execute
    result = bootstrap_issue(mock_state, mock_project, issue_numbers=[999])
    
    # Assertions
    assert result is False
