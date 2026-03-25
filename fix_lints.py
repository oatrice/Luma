import re

files_to_fix = [
    "luma_core/agents/docs.py",
    "luma_core/agents/publisher.py",
    "luma_core/pre_coding_checker.py",
    "luma_core/state_manager.py",
    "luma_core/tools.py",
    "main.py"
]

for file in files_to_fix:
    with open(file, "r") as f:
        content = f.read()
    # Fix bare excepts
    content = re.sub(r'except:', "except Exception:", content)
    with open(file, "w") as f:
        f.write(content)

# Fix E701 in specific files
def fix_e701(filepath, pattern, replacement):
    with open(filepath, "r") as f:
        content = f.read()
    content = content.replace(pattern, replacement)
    with open(filepath, "w") as f:
        f.write(content)

fix_e701("luma_core/context_summarizer.py", 'if tag == "IMPORTANT": active_alert = "❗ IMPORTANT"', 'if tag == "IMPORTANT":\n                            active_alert = "❗ IMPORTANT"')
fix_e701("luma_core/context_summarizer.py", 'elif tag == "WARNING": active_alert = "⚠️ WARNING"', 'elif tag == "WARNING":\n                            active_alert = "⚠️ WARNING"')
fix_e701("luma_core/context_summarizer.py", "if line_clean.startswith('#'): continue", "if line_clean.startswith('#'):\n                        continue")

fix_e701("luma_core/github_client.py", 'if title: payload["title"] = title', 'if title:\n        payload["title"] = title')
fix_e701("luma_core/github_client.py", 'if body: payload["body"] = body', 'if body:\n        payload["body"] = body')

fix_e701("scripts/verify_token.py", 'if not headers: return False', 'if not headers:\n        return False')
fix_e701("tests/search_issues.py", 'if c.status in ["Done", "Closed"]: continue', 'if c.status in ["Done", "Closed"]:\n                continue')

print("Fixed.")
