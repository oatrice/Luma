import os
import sys
import argparse
import subprocess
from langchain_core.messages import HumanMessage
from luma_core.workflow import build_graph
from luma_core.config import TARGET_DIR
from luma_core.llm import get_llm
from luma_core.tools import update_android_version_logic
from luma_core.agents.reviewer import reviewer_agent

# Try to import GitHub Fetcher
try:
    from github_fetcher import fetch_issues, select_issue, convert_to_task, update_issue_status
except ImportError:
    fetch_issues = None
    print("⚠️ github_fetcher.py not found. GitHub features disabled.")

def get_ai_advice(issues):
    """AI Advisor for Issue Selection"""
    if not issues:
        return
        
    summary = "\n".join([f"- Issue #{i['number']}: {i['title']}\n  Body: {(i.get('body') or '')[:200]}..." for i in issues])
    
    prompt = f"""
    You are a Technical Project Manager. 
    Analyze the following GitHub Issues (Priority Tasks) and suggest the execution order.
    
    Tasks:
    {summary}
    
    Output:
    Provide a short recommendation (2-3 sentences per task).
    Be concise. Use bullet points.
    """
    
    llm = get_llm(temperature=0.5)
    response = llm.invoke([HumanMessage(content=prompt)])
    print("\n🔎 AI Recommendation:\n" + response.content)

def main():
    parser = argparse.ArgumentParser(description="Luma AI Architect")
    parser.add_argument("--github", action="store_true", help="Fetch task from GitHub Issues")
    parser.add_argument("--repo", type=str, default="oatrice/Tetris-Battle", help="GitHub Repository (user/repo)")
    args = parser.parse_args()

    # Build the Agent Graph
    app = build_graph()

    print("\n==============================")
    print("🤖 Luma AI Architect")
    print("==============================")

    while True:
        print("\n1. 📥 Select Next Issue (Start Coding)")
        print("2. 🚀 Create Pull Request (Deploy)")
        print("3. 🧐 Code Review (Local)")
        print("4. 📝 Update Docs (Standalone)")
        print("5. 🤖 Update Android Server Version")
        print("0. ❌ Exit")
        
        choice = input("\nSelect Option: ").strip()
        
        if choice == "0":
            print("👋 Bye!")
            break
            
        elif choice == "1":
            if not fetch_issues:
                print("❌ GitHub fetcher unavailable.")
                continue
                
            print(f"📡 Fetching issues from {args.repo}...")
            issues = fetch_issues(args.repo)
            selected_issue = select_issue(issues, ai_advisor=get_ai_advice)
            
            if selected_issue:
                print(f"🚀 Starting Task: {selected_issue['title']}")
                update_issue_status(selected_issue, "In Progress")
                
                initial_state = {
                    "task": convert_to_task(selected_issue),
                    "repo": args.repo,
                    "issue_data": selected_issue,
                    "iterations": 0
                }
                
                app.invoke(initial_state)
                print("✅ Workflow Complete.")
            else:
                print("❌ No issue selected.")

        elif choice == "2":
            print("🚀 Manual PR Creation Mode")
            # Create a state wrapper
            task = input("Enter Task/PR Description: ").strip()
            if not task:
                print("❌ Task description required.")
                continue
                
            state = {
                "task": task,
                "repo": args.repo,
                # We need to trick the publisher into thinking work is done or just usage of current git state
                "changes": {}, # No new code changes from Coder
                "issue_data": {}
            }
            
            # Import on demand to avoid circular deps if any (though unlikely here)
            from luma_core.agents.publisher import publisher_agent
            publisher_agent(state)

        elif choice == "3":
            # Local Code Review
            print("🧐 Local Code Reviewer")
            # Simplified logic: Review all git changes
            try:
                # 1. Get Diff
                diff_cmd = ["git", "diff", "HEAD"]
                diff_res = subprocess.run(diff_cmd, cwd=TARGET_DIR, capture_output=True, text=True)
                changes = {"local_diff.patch": diff_res.stdout}
                
                if not diff_res.stdout:
                    print("✅ No changes to review.")
                    continue
                
                # 2. Run Reviewer
                state = {"task": "Review local changes", "changes": changes}
                result = reviewer_agent(state)
                
                print("\n📝 Reviewer Feedback:")
                print(result.get("code_content", "No feedback."))
                print("-" * 30)
                
            except Exception as e:
                print(f"❌ Review failed: {e}")

        elif choice == "4":
            # Docs Only
            print("📝 Doc Update Mode")
            # Invoke Graph with 'skip_coder'
            state = {
                "task": "Update documentation for recent changes", 
                "skip_coder": True,
                "changes": {}
            }
            app.invoke(state)

        elif choice == "5":
            print("🤖 Update Android Server Version")
            version = input("Target Version (e.g. 1.1.7): ").strip()
            if version:
                update_android_version_logic(version)
            else:
                print("❌ Version required.")

if __name__ == "__main__":
    main()
