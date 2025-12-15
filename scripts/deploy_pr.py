import sys
import os
import argparse
import subprocess
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import github_fetcher
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from github_fetcher import create_pull_request
except ImportError:
    print("❌ Error: Could not import github_fetcher. Make sure you are running this from 'scripts' directory.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Deploy PR for Luma/Tetris Projects")
    parser.add_argument("--repo", default="oatrice/Tetris-Battle", help="GitHub Repository")
    parser.add_argument("--branch", required=True, help="Head Branch (Source)")
    parser.add_argument("--base", default="main", help="Base Branch (Target)")
    parser.add_argument("--title", required=True, help="PR Title")
    parser.add_argument("--desc", help="PR Description")
    parser.add_argument("--template", help="Path to PR template")
    
    args = parser.parse_args()

    print(f"🚀 Deploying PR for {args.repo} ({args.branch} -> {args.base})...")

    # Body Logic
    body = args.desc or "Auto-generated PR"
    
    if args.template and os.path.exists(args.template):
         with open(args.template, "r") as f:
            template = f.read()
            # Simple replacements
            if args.desc:
                template = template.replace("<!-- Brief description of changes -->", args.title) # Use title as summary fallback
                template = template.replace("<!-- Describe what changed -->", args.desc)
                
                # Auto-check boxes based on title keywords
                lower_title = args.title.lower()
                if "feat" in lower_title:
                     template = template.replace("- [ ] ✨ New feature", "- [x] ✨ New feature")
                if "fix" in lower_title:
                     template = template.replace("- [ ] 🐛 Bug fix", "- [x] 🐛 Bug fix")
                if "refactor" in lower_title:
                     template = template.replace("- [ ] 🔧 Refactoring", "- [x] 🔧 Refactoring")
                     
            body = template
            print(f"📄 Loaded Template from {args.template}")

    # No Git Operations needed if branch is already pushed.
    # We assume the user has pushed the branch. 
    # If not, create_pull_request might fail or we should push here?
    # Let's add a safety push?
    # Actually, let's keep it simple: assume branch is pushed or local exists.
    # If only local exists, we need to push.
    
    # We can try to push safely
    # This requires knowing the local path, which might vary. 
    # For now, let's assume 'create_pull_request' just calls API. The code must be on remote.
    
    # Executing Push just in case (optional, might fail if not in git dir)
    # subprocess.run(["git", "push", "origin", args.branch], cwd=os.getcwd(), check=False)

    url = create_pull_request(args.repo, args.title, body, args.branch, args.base)
    
    if url:
        print(f"✅ Pipeline Complete! PR: {url}")
    else:
        print("❌ Pipeline Failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
