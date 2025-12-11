
import sys
import os
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import github_fetcher
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from github_fetcher import create_pull_request
except ImportError:
    print("❌ Error: Could not import github_fetcher. Make sure you are running this from 'scripts' directory.")
    sys.exit(1)

TARGET_DIR = "/Users/oatrice/Software-projects/Tetris-Battle"
REPO_NAME = "oatrice/Tetris-Battle"

def run_git(args, cwd):
    print(f"🔹 Executing: {' '.join(args)}")
    subprocess.run(args, cwd=cwd, check=True)

def main():
    print(f"🚀 Starting Manual PR Deployment for {REPO_NAME}...")
    
    # Check for changes
    status = subprocess.run(["git", "status", "--porcelain"], cwd=TARGET_DIR, capture_output=True, text=True)
    if not status.stdout.strip():
        print("⚠️ No changes to commit. Exiting.")
        return

    # 1. Generate Branch
    timestamp = int(time.time())
    branch_name = f"luma-fix-manual-{timestamp}"
    
    try:
        # 2. Git Operations
        # run_git(["git", "checkout", "main"], cwd=TARGET_DIR) # Assuming main exists
        # run_git(["git", "pull"], cwd=TARGET_DIR)
        
        run_git(["git", "checkout", "-b", branch_name], cwd=TARGET_DIR)
        run_git(["git", "add", "."], cwd=TARGET_DIR)
        run_git(["git", "commit", "-m", "Luma Fix: Restart button overlapping refactor"], cwd=TARGET_DIR)
        run_git(["git", "push", "origin", branch_name], cwd=TARGET_DIR)
        
        # 3. Open PR
        print("📝 Opening PR...")
        pr_url = create_pull_request(
            repo_name=REPO_NAME,
            title="Fix: Restart button position and dynamic sizing",
            body="This PR fixes the issue where the Restart button overlaps with the frame.\nIt implements dynamic button sizing based on text width.\n\nAutomated by Luma Pipeline.",
            head_branch=branch_name,
            base_branch="main"
        )
        
        if pr_url:
            print(f"✅ Pipeline Complete! PR: {pr_url}")
            # Switch back to main?
            run_git(["git", "checkout", "main"], cwd=TARGET_DIR)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
