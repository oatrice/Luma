import os
import shutil
import json
import traceback
from luma_core.rules_loader import load_project_rules, validate_rules
from luma_core.preflight_checker import PreflightChecker

TEMP_DIR = "tests/temp_phase6_verify"
CONFIG_FILE = os.path.join(TEMP_DIR, ".luma_rules.json")

def setup():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)
    
    # Create a valid rules file
    rules = {
        "$schema": "https://luma.dev/schemas/rules-v1.json",
        "project_name": "TestPhase6",
        "version": "1.0.0",
        "preflight_checks": [
            {
                "id": "test_check",
                "type": "command",
                "command": "echo 'hello'",
                "required": True
            }
        ]
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(rules, f)

def test_rules_loader():
    print("Testing RulesLoader...")
    try:
        rules = load_project_rules(CONFIG_FILE)
        if rules["project_name"] == "TestPhase6":
            print("✅ Rules loaded successfully")
        else:
            print("❌ Rules loading failed content check")
            
        if validate_rules(rules, "schemas/luma_rules.schema.json"):
            print("✅ Rules validation passed")
        else:
            print("❌ Rules validation failed")
            
    except Exception as e:
        print(f"❌ RulesLoader raised exception: {e}")
        traceback.print_exc()

def test_preflight_integration():
    print("\nTesting PreflightChecker Integration...")
    try:
        # PreflightChecker should load rules from the file in init
        checker = PreflightChecker(TEMP_DIR, rules_file=".luma_rules.json")
        
        if len(checker.rules) == 1 and checker.rules[0]["id"] == "test_check":
             print("✅ PreflightChecker correctly loaded and ran the rule")
        else:
             print(f"❌ PreflightChecker failed to load rules. Rules found: {checker.rules}")

    except Exception as e:
        print(f"❌ PreflightChecker Integration raised exception: {e}")
        traceback.print_exc()

def cleanup():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    try:
        setup()
        test_rules_loader()
        test_preflight_integration()
    finally:
        cleanup()
