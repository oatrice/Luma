import subprocess
import json

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
