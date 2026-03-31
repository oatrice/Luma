import re

with open("luma_core/actions/workflow_actions.py", "r") as f:
    text = f.read()

# remove the specific debug lines
text = text.replace('    # print(f"DEBUG: step_roadmap={step_roadmap}, phase={state.phase}")\n', '')
text = text.replace('    print(f"DEBUG: step_archive={step_archive}, phase={state.phase}")\n', '')
text = text.replace('        print(f"DEBUG: user_input={user_input}")\n        \n', '')

with open("luma_core/actions/workflow_actions.py", "w") as f:
    f.write(text)

with open("tests/test_action_guided_workflow_resume.py", "r") as f:
    text = f.read()

# Rewrite the side_effect logic to just be the list
old_code = """        _side_effect_list = ["y", "y", "y", "y", "y", "n", "n", ""]
        def debug_input(prompt=""):
            val = _side_effect_list.pop(0) if _side_effect_list else ""
            print(f"DEBUG INPUT: {prompt} -> {val}")
            return val
        mock_input.side_effect = debug_input"""

new_code = '        mock_input.side_effect = ["y", "y", "y", "y", "y", "n", "n", ""]'

text = text.replace(old_code, new_code)
with open("tests/test_action_guided_workflow_resume.py", "w") as f:
    f.write(text)
