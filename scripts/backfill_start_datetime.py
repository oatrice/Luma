#!/usr/bin/env python3
"""
Backfill script for Luma Issue Metrics.
Fills in `start_datetime` for issues that are missing it.
Uses:
1. Earliest git commit date referencing the issue (e.g., `#123`).
2. GitHub pull request `createdAt` that refers to the issue.
3. Fallback: GitHub Issue `createdAt`.
"""

import json
import os
import subprocess
from datetime import datetime

METRICS_FILE = ".luma_metrics.json"

def run_cmd(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return ""

def get_issue_created_at(issue_number, repo):
    out = run_cmd(["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "createdAt"])
    if out:
        try:
            data = json.loads(out)
            return data.get("createdAt")
        except:
            pass
    return None

def get_earliest_commit_date(issue_number):
    out = run_cmd(["git", "log", f"--grep=#{issue_number}", "--reverse", "--format=%aI"])
    if out:
        lines = out.splitlines()
        for line in lines:
            if line.strip():
                return line.strip()
    return None

def main():
    if not os.path.exists(METRICS_FILE):
        print(f"Error: {METRICS_FILE} not found.")
        return

    with open(METRICS_FILE, "r") as f:
        store = json.load(f)

    issues = store.get("issues", {})
    updated_count = 0

    for issue_key, record in issues.items():
        if record.get("start_datetime"):
            continue

        issue_number = record.get("issue_number")
        repo = record.get("repository")
        
        if not issue_number or not repo:
            continue
            
        print(f"Processing #{issue_number} ({record.get('issue_title')})...")
        
        # 1. Try Git commit
        earliest_date = get_earliest_commit_date(issue_number)
        source = "git commit"
        
        # 2. Try GitHub Issue created at
        if not earliest_date:
            earliest_date = get_issue_created_at(issue_number, repo)
            source = "gh issue createdAt"

        if earliest_date:
            print(f"  -> Found start_datetime: {earliest_date} (from {source})")
            record["start_datetime"] = earliest_date
            
            # Recalculate actual_mandays if completed
            if record.get("actual_completion_date"):
                try:
                    start_dt = datetime.fromisoformat(earliest_date.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(record["actual_completion_date"].replace("Z", "+00:00"))
                    diff_days = (end_dt - start_dt).total_seconds() / 86400.0
                    record["actual_mandays"] = max(0.5, round(diff_days * 2) / 2.0)
                    print(f"  -> Recalculated actual_mandays: {record['actual_mandays']}")
                except Exception as e:
                    print(f"  -> Failed to recalculate mandays: {e}")
                    
            updated_count += 1
        else:
            print(f"  -> Could not determine start_datetime.")

    if updated_count > 0:
        with open(METRICS_FILE, "w") as f:
            json.dump(store, f, indent=2)
        print(f"\nSuccessfully backfilled {updated_count} issues.")
    else:
        print("\nNo issues needed backfilling.")

if __name__ == "__main__":
    main()
