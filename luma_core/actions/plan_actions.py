import os
from luma_core.ui import safe_input
from luma_core.state_manager import LumaState
from .utils import (
    generate_draft_code_review
)

def action_refine_issue(state: LumaState, project: dict):
    """Run Analyst Agent to refine issue"""
    if not state.active_issue:
        print("❌ No active issue selected to refine.")
        return

    # Enable Analyst Agent
    try:
        from luma_core.agents.analyst import analyst_agent
    except ImportError:
        print("❌ Analyst agent not available.")
        return

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join(
        [f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues]
    )

    # Create temporary state
    analyst_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
        },
        "target_dir": project["path"],
        "target_planning_repos": state.context.get("target_planning_repos", []),
    }

    print("\n🧠 Invoking Analyst Agent...")
    result = analyst_agent(analyst_state)

    if result.get("analysis_file"):
        print(f"\n✨ Analysis complete! Document saved to: {result['analysis_file']}")
    else:
        print("\n⚠️ Analysis failed or produced no output.")

def action_generate_sbe(state: LumaState, project: dict):
    """Generate SBE (Specification by Example) for current issue"""
    if not state.active_issue:
        print("❌ No active issue selected.")
        print("💡 Select an issue first (Menu option 2)")
        return

    print("\n📋 SBE (Specification by Example) Generator")
    print(f"   Issue: #{state.active_issue.number} {state.active_issue.title}")

    # Enable SBE Agent
    try:
        from luma_core.agents.sbe_agent import sbe_agent
    except ImportError as e:
        print(f"❌ SBE agent not available: {e}")
        return

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join(
        [f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues]
    )

    first_issue = issues[0]

    # Create state for SBE agent
    sbe_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
            "url": getattr(first_issue, "html_url", ""),
            "repository": getattr(first_issue, "repository", ""),
        },
        "target_dir": project["path"],
    }

    print("\n🤖 Invoking SBE Agent (Integration -> Spec Agent)...")
    # Redirect legacy SBE to new Spec Agent if possible, or keep separate for now.
    # For now, let's keep SBE as a sub-feature, but we encourage using the full Spec Agent.
    result = sbe_agent(sbe_state)

    if result.get("sbe_file"):
        print("\n✨ SBE Specification created!")
        print(f"   📁 File: {result['sbe_file']}")

        # Preview first few lines
        try:
            with open(result["sbe_file"], "r") as f:
                lines = f.readlines()[:15]
                print("\n📄 Preview:")
                print("-" * 50)
                for line in lines:
                    print(line.rstrip())
                if len(lines) >= 15:
                    print("...")
                print("-" * 50)
        except Exception:
            pass
    else:
        print("\n⚠️ SBE generation failed or produced no output.")

def action_generate_draft(state: LumaState, project: dict):
    """Generate draft_code_review.md with full diff context"""
    print("\n📊 Generating Draft Code Review...")

    try:
        output_path = generate_draft_code_review(project["path"])
        print(f"\n✅ Draft saved to: {output_path}")
        print("   💡 This file can be used for PR creation and code review.")
        print("   📋 Publisher Agent will automatically use this file if present.")

        # Open in VS Code
        import subprocess

        try:
            subprocess.run(["code", output_path], capture_output=True)
            print("   📂 Opened in VS Code")
        except Exception:
            pass

    except Exception as e:
        print(f"\n❌ Failed to generate draft: {e}")

def action_generate_spec(state: LumaState, project: dict):
    """Generate spec.md using Spec Agent"""
    if not state.active_issue:
        print("❌ No active issue selected.")
        return

    # Enable Spec Agent
    try:
        from luma_core.agents.spec_agent import spec_agent
    except ImportError as e:
        print(f"❌ Spec agent not available: {e}")
        return

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join(
        [f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues]
    )

    # Use the first issue's URL and repository for simplicity
    first_issue = issues[0]

    # Create State
    spec_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
            "url": getattr(first_issue, "html_url", ""),
            "repository": getattr(first_issue, "repository", ""),
        },
        "target_dir": project["path"],
        "target_planning_repos": state.context.get("target_planning_repos", []),
    }

    print("\n🧬 Invoking Spec Agent (Spec Kit)...")
    result = spec_agent(spec_state)

    if result.get("feature_dir"):
        # Update state with feature dir for subsequent steps
        # In a real app, we might want to persist this in LumaState
        print(f"   📂 Feature Directory: {result['feature_dir']}")

        # Determine relative path for display
        os.path.relpath(result["feature_dir"], project["path"])
        # Store in state for Plan Agent to use immediately
        state.context["last_feature_dir"] = result["feature_dir"]
        print("   💡 Tip: Now you can generate the Plan (Menu Option 'P').")

    # Chain SBE Generation
    # Chain SBE Generation
    print("\n------------------------------------------------")
    print("📋 Auto-generating Specification by Example (SBE)...")
    from luma_core import usage_tracker
    if usage_tracker.get_current_sub_action() == "Auto:Planning/Spec":
        usage_tracker.set_sub_action("Auto:Planning/SBE")
    action_generate_sbe(state, project)

def action_generate_plan(state: LumaState, project: dict):
    """Generate plan.md using Architect Agent"""
    # Try to find feature dir: 1. From context, 2. Ask user
    feature_dir = state.context.get("last_feature_dir")

    if not feature_dir:
        # Simple heuristic: Look for valid feature dirs in docs/features
        # and ask user to pick
        features_root = os.path.join(project["path"], "docs", "features")
        if not os.path.exists(features_root):
            print("❌ No features directory found.")
            return

        dirs = [
            d
            for d in os.listdir(features_root)
            if os.path.isdir(os.path.join(features_root, d))
        ]
        if not dirs:
            print("❌ No feature directories found.")
            return

        print("\n📂 Select Feature to Plan:")
        for i, d in enumerate(dirs, 1):
            print(f"  [{i}] {d}")

        choice = safe_input("Select: ")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(dirs):
                feature_dir = os.path.join(features_root, dirs[idx])
            else:
                return
        except Exception:
            return

    # Enable Architect Agent
    try:
        from luma_core.agents.architect_agent import architect_agent
    except ImportError as e:
        print(f"❌ Architect agent not available: {e}")
        return

    # Create State
    plan_state = {
        "feature_dir": feature_dir, 
        "target_dir": project["path"],
        "target_planning_repos": state.context.get("target_planning_repos", []),
    }

    print("\n🏗️ Invoking Architect Agent...")
    result = architect_agent(plan_state)

    if result.get("plan_file"):
        print(f"\n✨ Plan created at: {result['plan_file']}")
