
import sys
import os
from unittest.mock import patch

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../")

from luma_core.github_project import KanbanCard
from main import action_list_active_issues

def verify_list_active():
    print("🧪 Verifying List Active Issues...")

    # Mock Project
    project = {"name": "Test Project", "kanban_number": 1}

    # Mock Cards
    cards = [
        KanbanCard(item_id="1", issue_number=101, title="Task Done", status="Done", repository="repo", url="url"),
        KanbanCard(item_id="2", issue_number=102, title="Task In Progress", status="In Progress", repository="repo", url="url"),
        KanbanCard(item_id="3", issue_number=103, title="Task Ready", status="Ready", repository="repo", url="url"),
        KanbanCard(item_id="4", issue_number=104, title="Task Backlog", status="Backlog", repository="repo", url="url"),
        KanbanCard(item_id="5", issue_number=105, title="Task Closed", status="Closed", repository="repo", url="url"),
    ]

    # Patch fetch_kanban_cards
    with patch("main.fetch_kanban_cards", return_value=cards):
        print("\n--- Expected Output: In Progress, Ready, Backlog (Sorted) ---")
        action_list_active_issues(project)
        print("-------------------------------------------------------------")

if __name__ == "__main__":
    verify_list_active()
