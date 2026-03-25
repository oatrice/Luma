import os
import shutil
import json
import subprocess
import sys
from luma_core.preflight_checker import PreflightChecker

# Setup
TEST_DIR = "temp_verification_project"
RULES_FILE = ".luma_rules.json"

def setup_env():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    
    # Git init
    subprocess.run(["git", "init"], cwd=TEST_DIR, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=TEST_DIR)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=TEST_DIR)
    
    # Create rules
    rules = {
        "project": "Test Project",
        "preflight_checks": [
            {
                "id": "check_readme",
                "name": "README Exists",
                "type": "file_exists",
                "path": "README.md",
                "required": True
            },
            {
                "id": "check_version",
                "name": "Version Bumped",
                "type": "version_updated",
                "path": "package.json",
                "required": True
            }
        ]
    }
    with open(os.path.join(TEST_DIR, RULES_FILE), "w") as f:
        json.dump(rules, f)
        
    print(f"✅ Setup temporary project in {TEST_DIR}")

def print_results(results):
    print("-" * 30)
    for r in results:
        icon = "✅" if r.passed else "❌"
        print(f"{icon} {r.name}: {r.message}")
    print("-" * 30)

def verify_scenario_1_fail():
    print("\n🔹 Scenario 1: Initial state (Should Fail files missing)")
    # No README, No package.json
    checker = PreflightChecker(TEST_DIR)
    results = checker.run_checks()
    print_results(results)
    
    # Assertions
    readme_check = next(r for r in results if r.check_id == "check_readme")
    assert not readme_check.passed, "README check should fail"

def verify_scenario_2_file_exists():
    print("\n🔹 Scenario 2: Create files (README Pass, Version Fail)")
    # Create README
    with open(os.path.join(TEST_DIR, "README.md"), "w") as f:
        f.write("# Hello")
    
    # Create package.json (Base version)
    with open(os.path.join(TEST_DIR, "package.json"), "w") as f:
        json.dump({"version": "1.0.0"}, f, indent=2)
        
    # Commit baseline
    subprocess.run(["git", "add", "."], cwd=TEST_DIR, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=TEST_DIR, capture_output=True)
    
    checker = PreflightChecker(TEST_DIR)
    results = checker.run_checks()
    print_results(results)
    
    readme_check = next(r for r in results if r.check_id == "check_readme")
    version_check = next(r for r in results if r.check_id == "check_version")
    
    assert readme_check.passed, "README check should pass"
    assert not version_check.passed, "Version check should fail (no change)"

def verify_scenario_3_version_bump():
    print("\n🔹 Scenario 3: Bump Version (Should Pass All)")
    
    # Modify package.json
    with open(os.path.join(TEST_DIR, "package.json"), "w") as f:
        json.dump({"version": "1.0.1"}, f, indent=2)
        
    # Check unstaged
    checker = PreflightChecker(TEST_DIR)
    results = checker.run_checks()
    print_results(results)
    
    version_check = next(r for r in results if r.check_id == "check_version")
    assert version_check.passed, "Version check should pass with unstaged changes"

def cleanup():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    print("\n🧹 Cleanup complete")

def main():
    try:
        setup_env()
        verify_scenario_1_fail()
        verify_scenario_2_file_exists()
        verify_scenario_3_version_bump()
        print("\n✨ All verification scenarios passed!")
    except AssertionError as e:
        print(f"\n❌ Verification Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        cleanup()

if __name__ == "__main__":
    main()
