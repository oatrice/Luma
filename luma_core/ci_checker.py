import subprocess
import json
import time

from luma_core.notifier import notify_task_complete

def check_pr_ci_status(pr_number: str, repo: str) -> dict:
    cmd = ["gh", "pr", "checks", str(pr_number), "--repo", repo, "--json", "name,state,conclusion"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"all_passed": False, "checks": [], "failed_checks": []}
    
    try:
        checks = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"all_passed": False, "checks": [], "failed_checks": []}

    failed_checks = [c for c in checks if c.get("conclusion", "").upper() in ("FAILURE", "TIMED_OUT", "STARTUP_FAILURE", "ACTION_REQUIRED")]
    
    # Check if there are checks, and none of them failed. We also consider "all_passed" true if there are genuinely no failed checks, 
    # but there must be at least one check completed. 
    # Note: state indicates COMPLETED, IN_PROGRESS, etc.
    in_progress = any(c.get("state", "").upper() != "COMPLETED" for c in checks)
    
    # For CI to be fully passed: no in-progress jobs, no failed jobs, and there should be some checks.
    all_passed = len(failed_checks) == 0 and not in_progress and len(checks) > 0

    return {
        "all_passed": all_passed,
        "checks": checks,
        "failed_checks": failed_checks,
        "in_progress": in_progress
    }

def get_ci_failure_logs(pr_number: str, repo: str, check_name: str, max_length: int = 3000) -> str:
    # First, get the run databaseId for this check using gh run list
    cmd = ["gh", "run", "list", "--repo", repo, "--limit", "10", "--json", "databaseId,name,conclusion"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return "Failed to fetch run list."
        
    try:
        runs = json.loads(result.stdout)
    except json.JSONDecodeError:
        return "Failed to parse run list JSON."

    run_id = None
    for run in runs:
        if run.get("name") == check_name and run.get("conclusion", "").upper() == "FAILURE":
            run_id = run["databaseId"]
            break
            
    if not run_id:
        return "Could not determine run_id for failure logs."
        
    # Get logs
    log_cmd = ["gh", "run", "view", str(run_id), "--repo", repo, "--log-failed"]
    log_result = subprocess.run(log_cmd, capture_output=True, text=True)
    
    out = log_result.stdout if log_result.returncode == 0 else (log_result.stderr or log_result.stdout)

    if len(out) > max_length:
        trunc_msg = "\n...[truncated by luma]..."
        allowed_len = max_length - len(trunc_msg) - 3
        out = "..." + out[-allowed_len:] + trunc_msg
        
    return out

def monitor_ci_background(pr_number: str, repo: str, project_name: str, pr_url: str, max_polls: int = 20, poll_interval_sec: int = 30):
    for attempt in range(1, max_polls + 1):
        status = check_pr_ci_status(pr_number, repo)
        if status["all_passed"]:
            notify_task_complete(
                project=project_name,
                task=f"CI Check for PR #{pr_number}",
                status="success",
                link=pr_url
            )
            return
        elif len(status["failed_checks"]) > 0:
            first_fail = status["failed_checks"][0].get("name", "Unknown")
            fail_log = get_ci_failure_logs(pr_number, repo, first_fail)
            
            ai_context = f"The CI check `{first_fail}` failed for my PR on {repo}.\nHere is the log:\n```\n{fail_log}\n```\nHow should I fix this?"
            
            notify_task_complete(
                project=project_name,
                task=f"CI Check for PR #{pr_number} ({first_fail})",
                status="failure",
                message=ai_context,
                link=pr_url
            )
            return
            
        time.sleep(poll_interval_sec)
        
    # Timeout
    notify_task_complete(
        project=project_name,
        task=f"CI Check for PR #{pr_number}",
        status="failure",
        message="CI check timed out after maximum polls.",
        link=pr_url
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Monitor CI status in background")
    parser.add_argument("pr_number", help="PR Number")
    parser.add_argument("repo", help="Repository (e.g. org/repo)")
    parser.add_argument("project_name", help="Project name for notification")
    parser.add_argument("pr_url", help="PR URL for notification")
    
    args = parser.parse_args()
    
    monitor_ci_background(args.pr_number, args.repo, args.project_name, args.pr_url)
