import json
import subprocess
from datetime import datetime, timedelta

def get_github_issue_dates(repo, issue_number):
    try:
        cmd = ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "createdAt,closedAt"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data.get("createdAt"), data.get("closedAt")
    except Exception:
        return None, None

def parse_iso(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None

def main():
    metrics_file = "/Users/oatrice/Software-projects/The Middle Way -Metadata/.luma_metrics.json"
    with open(metrics_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = data.get("issues", {})
    updated = 0

    print("Fixing anomalies in .luma_metrics.json...")

    for issue_id, record in issues.items():
        repo = record.get("repository", "")
        num = record.get("issue_number")
        if not repo or not num:
            continue
            
        status = record.get("issue_status", "")
        # 1. Clear actual_mandays for closed/duplicated issues
        if "Closed(duplicated with" in status or "❌ Closed" in status:
            if record.get("actual_mandays", 0) > 0:
                print(f"[#{num}] Resetting actual_mandays to 0 for duplicated issue")
                record["actual_mandays"] = 0.0
                updated += 1

        # Fix Time Paradox
        end_str = record.get("actual_completion_date")
        start_str = record.get("start_datetime")
        created_str = record.get("created_at")
        
        end_dt = parse_iso(end_str)
        start_dt = parse_iso(start_str)
        created_dt = parse_iso(created_str)

        # 2. Resync created_at from GitHub (especially those created on 2026-03-20 migration)
        gh_created, gh_closed = get_github_issue_dates(repo, num)
        if gh_created and gh_created != created_str:
            # We trust GitHub's original creation date more than the local migration date, 
            # EXCEPT if the local creation date was earlier (e.g. created locally before migrated)
            gh_created_dt = parse_iso(gh_created)
            if created_dt and gh_created_dt and gh_created_dt < created_dt:
                print(f"[#{num}] Resyncing created_at from {created_str} -> {gh_created}")
                record["created_at"] = gh_created
                created_str = gh_created
                created_dt = gh_created_dt
                updated += 1
            elif not created_dt:
                print(f"[#{num}] Setting missing created_at -> {gh_created}")
                record["created_at"] = gh_created
                created_str = gh_created
                created_dt = gh_created_dt
                updated += 1

        # 3. Handle actual_completion_date < start_datetime or created_at
        # We assume `actual_completion_date` (often close to gh_closed) is the most accurate event
        if end_dt:
            # If actual_completion_date < start_datetime, we fix start_datetime by subtracting estimated mandays
            if start_dt and end_dt < start_dt:
                mandays = record.get("estimated_mandays", 0.5)
                # Ensure at least 0.5 days diff
                mandays = max(0.5, mandays)
                new_start_dt = end_dt - timedelta(days=mandays)
                # Format to ISO
                new_start_str = new_start_dt.isoformat().replace("+00:00", "Z")
                print(f"[#{num}] Fixing Time Paradox: start_datetime {start_str} -> {new_start_str}")
                record["start_datetime"] = new_start_str
                updated += 1
            
            # If actual_completion_date < created_at, fixing created_at to before end_dt
            # But normally created_at should not change if it's from GitHub...
            # This is just an edge case for local issues that were pushed later.
            elif created_dt and end_dt < created_dt:
                # Same logic, let's push created_at back
                new_created_dt = end_dt - timedelta(days=record.get("estimated_mandays", 0.5))
                new_created_str = new_created_dt.isoformat().replace("+00:00", "Z")
                print(f"[#{num}] Fixing Creation Paradox: created_at {created_str} -> {new_created_str}")
                record["created_at"] = new_created_str
                updated += 1

    if updated > 0:
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nFixed {updated} data points. Please review changes in {metrics_file}")
    else:
        print("\nNo anomalies needed fixing.")

if __name__ == "__main__":
    main()
