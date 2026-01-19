import os
import shutil
import json
from luma_core.context_summarizer import ContextSummarizer

def setup_dummy_project():
    path = "dummy_phase4"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    os.makedirs(os.path.join(path, ".agent", "rules"))
    
    # Create .luma_rules.json
    rules = {
        "context_rules": ["Remember to run tests before pushing"],
        "preflight_checks": [
            {"name": "Check Version", "required": True, "message": "Version must be updated"}
        ]
    }
    with open(os.path.join(path, ".luma_rules.json"), "w") as f:
        json.dump(rules, f)
        
    # Create markdown rule
    md_content = """
    # Coding Standards
    - You MUST use snake_case for functions.
    - You SHOULD add docstrings.
    > [!IMPORTANT]
    > Do not commit secrets.
    """
    with open(os.path.join(path, ".agent", "rules", "coding.md"), "w") as f:
        f.write(md_content)
        
    return path

def verify_summarizer():
    path = setup_dummy_project()
    print(f"📁 Created dummy project at {path}")
    
    print("\n🧠 Loading Project Context...")
    try:
        summarizer = ContextSummarizer(path)
        reminders = summarizer.summarize_rules()
        
        print("\n📝 Project Reminders & Rules (Expected Output):")
        if reminders:
            for r in reminders:
                print(f"  {r}")
        else:
            print("  No specific rules found.")
            
        # Assertions to ensure it works
        assert any("run tests" in r for r in reminders)
        assert any("Version must be updated" in r for r in reminders)
        assert any("MUST: You MUST use snake_case" in r for r in reminders)
        assert any("IMPORTANT: Do not commit secrets" in r for r in reminders)
        print("\n✅ Verification Successful!")
        
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
    finally:
        if os.path.exists(path):
            shutil.rmtree(path)

if __name__ == "__main__":
    verify_summarizer()
