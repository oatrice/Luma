#!/usr/bin/env python3
"""
Backfill `start_datetime` from `.luma_ai_usage.jsonl`.
Finds the earliest AI usage timestamp for each issue.
"""

import json
import os
import sys
from datetime import datetime

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 backfill_from_usage.py <usage_file.jsonl> <metrics_file.json>")
        return

    USAGE_FILE = sys.argv[1]
    METRICS_FILE = sys.argv[2]

    if not os.path.exists(USAGE_FILE):
        print(f"Error: {USAGE_FILE} not found.")
        return
        
    if not os.path.exists(METRICS_FILE):
        print(f"Error: {METRICS_FILE} not found.")
        return

    # 1. Parse usage file to find earliest timestamp for each issue
    # We will map (project_repo, issue_number) -> earliest_ts
    # E.g., ("oatrice/Luma", 1) -> "2026-03-18T10:00:00Z"
    earliest_times = {}
    
    with open(USAGE_FILE, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                ts = data.get("ts")
                repo = data.get("project_repo")
                issue_numbers = data.get("issue_numbers", [])
                
                if not ts or not repo or not issue_numbers:
                    continue
                    
                for num in issue_numbers:
                    key = (repo, num)
                    if key not in earliest_times or ts < earliest_times[key]:
                        earliest_times[key] = ts
            except json.JSONDecodeError:
                pass

    print(f"Found usage data for {len(earliest_times)} issues.")

    # 2. Update metrics file
    with open(METRICS_FILE, "r") as f:
        store = json.load(f)

    issues = store.get("issues", {})
    updated_count = 0

    for issue_key, record in issues.items():
        issue_number = record.get("issue_number")
        repo = record.get("repository")
        
        if not issue_number or not repo:
            continue
            
        lookup_key = (repo, issue_number)
        usage_ts = earliest_times.get(lookup_key)
        
        if usage_ts:
            current_start = record.get("start_datetime")
            
            # Update if empty OR if usage_ts is earlier than current_start
            should_update = False
            if not current_start:
                should_update = True
            else:
                # Compare timestamps (basic string comparison works for ISO8601)
                # Ensure they are comparable
                if usage_ts < current_start:
                    should_update = True
                    
            if should_update:
                print(f"Updating #{issue_number} ({record.get('issue_title')})")
                print(f"  Old start: {current_start}")
                print(f"  New start: {usage_ts}")
                
                record["start_datetime"] = usage_ts
                
                # Recalculate mandays if completed
                if record.get("actual_completion_date"):
                    try:
                        start_dt = datetime.fromisoformat(usage_ts.replace("Z", "+00:00")).replace(tzinfo=None)
                        end_dt = datetime.fromisoformat(record["actual_completion_date"].replace("Z", "+00:00")).replace(tzinfo=None)
                        diff_days = (end_dt - start_dt).total_seconds() / 86400.0
                        record["actual_mandays"] = max(0.5, round(diff_days * 2) / 2.0)
                        print(f"  -> Recalculated actual_mandays: {record['actual_mandays']}")
                    except Exception as e:
                        print(f"  -> Failed to recalculate mandays: {e}")
                
                updated_count += 1

    if updated_count > 0:
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully backfilled/updated {updated_count} issues from AI usage logs.")
    else:
        print("\nNo issues needed updating.")

if __name__ == "__main__":
    main()
