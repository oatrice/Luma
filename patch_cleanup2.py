import re

# 1. Fix luma_core/actions/workflow_actions.py debug prints (just to be absolutely safe)
with open("luma_core/actions/workflow_actions.py", "r") as f:
    text = f.read()

text = re.sub(r'[ \t]*# print\(f"DEBUG: step_roadmap=.*?\n', '', text)
text = re.sub(r'[ \t]*print\(f"DEBUG: step_archive=.*?\n', '', text)
text = re.sub(r'[ \t]*print\(f"DEBUG: user_input=.*?\n', '', text)
text = re.sub(r'[ \t]*print\(f"DEBUG: Failed to fetch issues.*?\n', '', text)

with open("luma_core/actions/workflow_actions.py", "w") as f:
    f.write(text)

# 2. Fix tests/test_action_guided_workflow_resume.py
with open("tests/test_action_guided_workflow_resume.py", "r") as f:
    text = f.read()

# remove the debug_input
text = re.sub(r'[ \t]*_side_effect_list.*?mock_input\.side_effect = debug_input', '        mock_input.side_effect = ["y", "y", "y", "y", "y", "n", "n", ""]', text, flags=re.DOTALL)

# Add patch for action_send_workflow_summary
if '@patch("luma_core.actions.workflow_actions.action_send_workflow_summary")' not in text:
    text = text.replace(
        '@patch("luma_core.actions.workflow_actions.action_create_pr")',
        '@patch("luma_core.actions.workflow_actions.action_send_workflow_summary")\n    @patch("luma_core.actions.workflow_actions.action_create_pr")'
    )
    text = text.replace(
        'mock_input, mock_pr, mock_archive',
        'mock_input, mock_pr, mock_summary, mock_archive'
    )

with open("tests/test_action_guided_workflow_resume.py", "w") as f:
    f.write(text)

