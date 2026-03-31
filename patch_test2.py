import re
with open("tests/test_action_guided_workflow_resume.py", "r") as f:
    text = f.read()

text = text.replace('["y", "y", "y", "y", "n", "n", ""]', '["y", "y", "y", "y", "y", "n", "n", ""]')
with open("tests/test_action_guided_workflow_resume.py", "w") as f:
    f.write(text)
