import os
from luma_core.state import LumaState
from luma_core.github_project import GitHubProject
from luma_core.actions.issue_actions import action_select_issue

state = LumaState.load()
project = GitHubProject()

try:
    action_select_issue(state, project)
except KeyboardInterrupt:
    print("\nInterrupted")
except Exception as e:
    print(f"Error: {e}")
