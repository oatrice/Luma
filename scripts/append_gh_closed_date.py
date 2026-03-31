import json
import subprocess
from datetime import datetime

metrics_file = "/Users/oatrice/Software-projects/The Middle Way -Metadata/.luma_metrics.json"

def get_github_issue_closed_at(repo, issue_number):
    try:
        cmd = ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "closedAt"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data.get("closedAt")
    except Exception:
        return None

def main():
    print(f"Reading {metrics_file}...")
    with open(metrics_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = data.get("issues", {})
    updated = 0

    print("Fetching 'closedAt' from GitHub for each issue...")
    for issue_id, record in issues.items():
        repo = record.get("repository", "")
        num = record.get("issue_number")
        if not repo or not num:
            continue
            
        # We only really care if it has an actual_completion_date or is complete/closed
        status = record.get("issue_status", "")
        if "Complete" in status or "Closed" in status or record.get("actual_completion_date"):
            # If we haven't already fetched it
            if "gh_closed_at" not in record:
                gh_closed = get_github_issue_closed_at(repo, num)
                if gh_closed:
                    print(f"[#{num}] Fetched closedAt from GitHub: {gh_closed}")
                    record["gh_closed_at"] = gh_closed
                    updated += 1
                else:
                    print(f"[#{num}] No closedAt found or issue is open on GitHub.")

    if updated > 0:
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully saved 'gh_closed_at' for {updated} issues.")
    else:
        print("\nNo issues needed updating or all were already fetched.")

if __name__ == "__main__":
    main()
