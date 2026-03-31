import re
with open("tests/test_action_guided_workflow_resume.py", "r") as f:
    text = f.read()

replacement = """
    _side_effect_list = ["y", "y", "y", "y", "n", "n", ""]
    def debug_input(prompt=""):
        val = _side_effect_list.pop(0) if _side_effect_list else ""
        print(f"DEBUG INPUT: {prompt} -> {val}")
        return val
    mock_input.side_effect = debug_input
"""

text = re.sub(r'mock_input\.side_effect = \["y", "y", "y", "y", "n", "n", ""\]', replacement.strip(), text)
with open("tests/test_action_guided_workflow_resume.py", "w") as f:
    f.write(text)
