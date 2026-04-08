#!/usr/bin/env python3
"""Debug: Check if action_status_map could be empty or cause Unknown action"""

import sys
sys.path.insert(0, '/Users/oatrice/.windsurf/worktrees/Luma/Luma-869eb936')

# Test 1: Empty dict causes "Unknown action"
print("=" * 60)
print("TEST 1: Empty action_status_map dict")
empty_map = {}
result = empty_map.get("select_issue")
print(f"   {{}}.get('select_issue') = {result}")
print(f"   'if not result' would be: {not result}")
print("   => This triggers 'Unknown action' warning!")

# Test 2: Dict with None value
print()
print("=" * 60)
print("TEST 2: Dict with None value")
none_map = {"select_issue": None}
result = none_map.get("select_issue")
print(f"   {{'select_issue': None}}.get('select_issue') = {result}")
print(f"   'if not result' would be: {not result}")
print("   => This also triggers 'Unknown action' warning!")

# Test 3: Dict with empty string value
print()
print("=" * 60)
print("TEST 3: Dict with empty string value")
empty_str_map = {"select_issue": ""}
result = empty_str_map.get("select_issue")
print(f"   {{'select_issue': ''}}.get('select_issue') = '{result}'")
print(f"   'if not result' would be: {not result}")
print("   => This also triggers 'Unknown action' warning!")

# Test 4: Check actual Luma workflow from PROJECTS
print()
print("=" * 60)
print("TEST 4: Check actual Luma project from PROJECTS dict")
from luma_core.config import PROJECTS
luma_project = PROJECTS.get("12")  # Luma is key "12"
if luma_project:
    sw = luma_project.get("status_workflow", {})
    print(f"   Project: {luma_project.get('name')}")
    print(f"   Repo: {luma_project.get('repo')}")
    print(f"   Has status_workflow: {'status_workflow' in luma_project}")
    print(f"   'action_status_map' in status_workflow: {'action_status_map' in sw}")
    if 'action_status_map' in sw:
        asm = sw['action_status_map']
        print(f"   action_status_map value: {asm}")
        print(f"   action_status_map type: {type(asm)}")
        print(f"   'select_issue' in map: {'select_issue' in asm if isinstance(asm, dict) else 'N/A (not dict)'}")
        if isinstance(asm, dict) and 'select_issue' in asm:
            print(f"   action_status_map['select_issue'] = {asm['select_issue']!r}")

print()
print("=" * 60)
print("CONCLUSION:")
print("If action_status_map is {} or has None/empty values,")
print("sync_kanban_on_action will show 'Unknown action: select_issue'")
