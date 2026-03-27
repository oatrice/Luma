with open("tests/test_action_guided_workflow_resume.py", "r") as f:
    text = f.read()

text = text.replace('\n    @patch("luma_core.actions.workflow_actions.action_create_pr")', '\n@patch("luma_core.actions.workflow_actions.action_create_pr")')

with open("tests/test_action_guided_workflow_resume.py", "w") as f:
    f.write(text)

