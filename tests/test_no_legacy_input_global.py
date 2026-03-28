import subprocess
import os
import re

TARGET_FILES = [
    "luma_core/tools.py",
    "luma_core/agents/publisher.py"
]

def test_no_standard_input_calls():
    project_root = "/Users/oatrice/Software-projects/Luma"
    # Unified pattern: matches 'input(' but not 'ui.safe_input('
    # We'll use re.search for more precision
    
    legacy_found = False
    for file_name in TARGET_FILES:
        file_path = os.path.join(project_root, file_name)
        if not os.path.exists(file_path):
            print(f"ERROR: File not found {file_path}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        file_legacy_calls = []
        for i, line in enumerate(lines):
            # 1. Ignore comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
                
            # 2. Look for 'input(' but not prefixed by 'ui.safe_'
            # We look for calls like 'input(', 'Var = input(', etc.
            # Avoid matching 'ui.safe_input'
            if "input(" in line and "ui.safe_input(" not in line:
                file_legacy_calls.append(f"{i+1}: {line.strip()}")
        
        if file_legacy_calls:
            print(f"FAILED: Found legacy input() in {file_name}:")
            for call in file_legacy_calls:
                print(f"  {call}")
            legacy_found = True
            
    if not legacy_found:
        print("PASSED: No legacy input() calls found.")
        return True
    return False

if __name__ == "__main__":
    if not test_no_standard_input_calls():
        exit(1)
