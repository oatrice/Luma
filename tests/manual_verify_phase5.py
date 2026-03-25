
import sys
import os
import time

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import display_header, display_menu, WorkflowPhase, LumaState, IssueData, clear_screen  # noqa: F401
except ImportError:
    print("❌ Error: Could not import Luma modules. Make sure you are running this from the project root or tests/ directory.")
    sys.exit(1)

def run_visual_verification():
    """
    Interactively steps through different UI states to allow manual verification.
    """
    
    scenarios = [
        {
            "phase": WorkflowPhase.IDLE,
            "issue": None,
            "branch": None,
            "desc": "Scene 1: IDLE State\n- Header should show 'Idle'\n- Menu: Select Issue should be active.\n- Menu: Create PR should be disabled."
        },
        {
            "phase": WorkflowPhase.CODING,
            "issue": IssueData(
                number=42, 
                title="Implement Dark Mode", 
                html_url="http://github.com/example/issue/42", 
                body="User wants dark mode", 
                project_item_id="1", 
                project_id="1", 
                repository="oatrice/Luma"
            ),
            "branch": "feat/42-dark-mode",
            "desc": "Scene 2: CODING State\n- Header should show '🔨 Coding', Task #42, and Branch.\n- Menu: Create PR, Code Review should be active."
        },
        {
            "phase": WorkflowPhase.PR_PENDING,
            "issue": IssueData(
                number=42, 
                title="Implement Dark Mode", 
                html_url="http://github.com/example/issue/42", 
                body="User wants dark mode", 
                project_item_id="1", 
                project_id="1", 
                repository="oatrice/Luma"
            ),
            "branch": "feat/42-dark-mode",
            "desc": "Scene 3: PR PENDING State\n- Header should show '🚀 PR Pending'.\n- Menu: Code Review active."
        }
    ]

    project = {"name": "JarWise (Simulation)", "path": "/tmp"}
    state = LumaState()

    print("\n🕵️  Starting Manual UI Verification Tour...")
    time.sleep(1)

    for i, scene in enumerate(scenarios, 1):
        # Update State
        state.phase = scene["phase"]
        state.active_issue = scene["issue"]
        state.active_branch = scene["branch"]

        # 1. Clear Screen & Display
        display_header(state, project)
        display_menu(state)

        # 2. Show Verification Prompt
        print("\n" + "="*60)
        print(f"👀 VERIFICATION CHECKLIST ({i}/{len(scenarios)})")
        print(scene["desc"])
        print("="*60)
        
        input("\nPress [Enter] to continue to next scene...")

    print("\n✅ Verification Tour Completed.")
    print("If all screens looked correct, Phase 5 is verified!")

if __name__ == "__main__":
    run_visual_verification()
