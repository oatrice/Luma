import os
import shutil
from luma_core.ui import safe_input
from luma_core.state_manager import LumaState
from luma_core.config import PROJECTS
from luma_core.issue_metrics import _humanize_feature_slug
from luma_core.tools import resolve_project_target_dir
from .utils import (
    sync_kanban_on_action,
    _add_new_project
)

def action_test_telegram_notification(state: LumaState, project: dict):
    """Test sending a Telegram notification directly from the CLI."""
    from luma_core import ui
    from luma_core.notifier import notify_task_complete
    
    ui.display_header(state, project)
    
    project_name = project["name"] if project else "Luma"
    
    result = notify_task_complete(
        project=project_name,
        task="Test Telegram Notification",
        status="success",
        duration="1s",
        message="🧪 ทดสอบการส่งข้อความจากเมนู Luma CLI"
    )
    
    if result:
        print("\n✅ Notification sent successfully!")
    else:
        print("\n❌ Failed to send notification (Check AKASA_CHAT_ID or backend config).")
    
    safe_input("\nPress Enter to return to menu...")

def action_sync_ai_brain(state: LumaState, project: dict, headless: bool = False) -> bool:
    """Manually trigger AI Brain Sync with preview + confirm + session picker. Supports Antigravity and Gemini CLI."""
    if not state.active_issue:
        if not headless:
            print("❌ No active issue selected. Please select an issue first.")
        return False

    if not headless:
        print(f"\n🧠 Syncing AI Agent Brain Artifacts for {project['name']}...")
    all_synced_docs = []

    # 1. Try Antigravity Brain
    try:
        from luma_core.ai_brain_sync import AntigravityBrain, GeminiCLIBrain

        sessions = AntigravityBrain.get_all_sessions(project.get("path"))
        if sessions:
            # Preview latest session
            latest = sessions[0]
            if not headless:
                print(
                    f"\n   📂 [Antigravity] Latest Session: {latest['session_id'][:12]}..."
                )
                print(f"   📄 Preview: {latest['preview']}")

                confirm = (
                    safe_input("\n   ✅ Use this Antigravity session? (Y/n/s to skip): ")
                    .lower()
                )
            else:
                confirm = "y" # Auto-use latest in headless

            if confirm != "s":
                selected_path = latest["path"]

                if not headless and confirm == "n":
                    # Show session picker
                    print("\n   📋 Available Antigravity Sessions:")
                    display_limit = min(8, len(sessions))
                    for i, s in enumerate(sessions[:display_limit]):
                        print(
                            f"   [{i + 1}] {s['session_id'][:12]}... — {s['preview'][:50]}"
                        )

                    choice = (
                        safe_input(
                            f"\n   Select session [1-{display_limit}] or [c] Cancel: "
                        )
                        .lower()
                    )
                    if choice != "c" and choice:
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < display_limit:
                                selected_path = sessions[idx]["path"]
                                print(
                                    f"   🔗 Selected: {sessions[idx]['session_id'][:12]}..."
                                )
                                synced_antigravity = AntigravityBrain.sync_to_repo(
                                    resolve_project_target_dir(project["path"]),
                                    state.active_issue.number,
                                    session_path=selected_path,
                                )
                                all_synced_docs.extend(synced_antigravity)
                                state.context["selected_brain_session"] = selected_path
                        except ValueError:
                            pass
                else:
                    synced_antigravity = AntigravityBrain.sync_to_repo(
                        resolve_project_target_dir(project["path"]),
                        state.active_issue.number,
                        session_path=selected_path,
                    )
                    all_synced_docs.extend(synced_antigravity)
                    state.context["selected_brain_session"] = selected_path
        elif not headless:
            print("ℹ️ No Antigravity sessions found.")

    except Exception as e:
        if not headless:
            print(f"⚠️ Antigravity sync failed: {e}")

    # 2. Try Gemini CLI Brain
    try:
        from luma_core.ai_brain_sync import GeminiCLIBrain

        if not headless:
            print("\n   🔍 Checking Gemini CLI session artifacts...")

        gemini_sessions = GeminiCLIBrain.get_all_sessions(project.get("path"))
        if gemini_sessions:
            latest = gemini_sessions[0]
            if not headless:
                print(
                    f"\n   📂 [Gemini CLI] Latest Session: {latest['session_id'][:12]}..."
                )
                print(f"   📄 Preview: {latest['preview'][:80]}")

                confirm = (
                    safe_input("\n   ✅ Sync this Gemini CLI session? (Y/n/s to skip): ")
                    .lower()
                )
            else:
                confirm = "y" # Auto-sync in headless

            if confirm != "s":
                selected_path = latest["path"]

                if not headless and confirm == "n":
                    # Show session picker
                    print("\n   📋 Available Gemini CLI Sessions:")
                    display_limit = min(8, len(gemini_sessions))
                    for i, s in enumerate(gemini_sessions[:display_limit]):
                        print(
                            f"   [{i + 1}] {s['session_id'][:12]}... — {s['preview'][:60]}"
                        )

                    choice = (
                        safe_input(
                            f"\n   Select session [1-{display_limit}] or [c] Cancel: "
                        )
                        .lower()
                    )
                    if choice != "c" and choice:
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < display_limit:
                                selected_path = gemini_sessions[idx]["path"]
                                print(
                                    f"   🔗 Selected: {gemini_sessions[idx]['session_id'][:12]}..."
                                )
                                synced_gemini = GeminiCLIBrain.sync_to_repo(
                                    resolve_project_target_dir(project["path"]),
                                    state.active_issue.number,
                                    session_path=selected_path,
                                )
                                all_synced_docs.extend(synced_gemini)
                        except ValueError:
                            pass
                else:
                    synced_gemini = GeminiCLIBrain.sync_to_repo(
                        resolve_project_target_dir(project["path"]),
                        state.active_issue.number,
                        session_path=selected_path,
                    )
                    all_synced_docs.extend(synced_gemini)
        elif not headless:
            print("   ℹ️ No Gemini CLI session artifacts found.")
    except Exception as e:
        if not headless:
            print(f"⚠️ Gemini CLI sync failed: {e}")

    if all_synced_docs:
        if not headless:
            print(
                f"\n✅ Successfully synced {len(all_synced_docs)} files from AI Brain(s)."
            )
            for doc in all_synced_docs:
                print(f"  - {doc}")
            print(
                "💡 The files have been copied to the project. You can review and commit them manually."
            )
        return True
    else:
        if not headless:
            print("\n⚠️ No new artifacts to sync (content unchanged or no sources found).")
        return False

def action_switch_project(state: LumaState) -> str:
    """Switch to different project"""
    # Collect all sibling repo keys to hide from menu
    sibling_keys = set()
    for key, proj in PROJECTS.items():
        for sib_key in proj.get("sibling_repos", []):
            sibling_keys.add(str(sib_key))

    print("\n🔀 Select Project:")
    for key, proj in PROJECTS.items():
        if key in sibling_keys:
            continue  # Hide sibling repos from menu
        print(f"  [{key}] {proj['name']}")

    print("  [+] Add New Project")

    choice = safe_input("\nSelect: ")

    if choice == "+":
        return _add_new_project(state)

    if choice in PROJECTS:
        return choice

    return None

def _list_github_projects():
    """Fetch and display GitHub Projects with their Number and ID from GitHub API."""
    import subprocess
    import json
    
    print("\n📋 GitHub Projects (from GitHub API)")
    print("=" * 60)
    print("Fetching projects from GitHub API...")
    
    # GraphQL query to get user's projects
    query = '''query {
      viewer {
        projectsV2(first: 20) {
          nodes {
            id
            number
            title
            url
          }
        }
      }
    }'''
    
    try:
        result = subprocess.run(
            ['gh', 'api', 'graphql', '-f', f'query={query}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"❌ Error fetching projects: {result.stderr}")
            print("\n💡 Make sure you have:")
            print("   1. GitHub CLI installed (gh)")
            print("   2. Authenticated with 'gh auth login'")
            return
        
        data = json.loads(result.stdout)
        projects = data.get('data', {}).get('viewer', {}).get('projectsV2', {}).get('nodes', [])
        
        if not projects:
            print("ℹ️  No GitHub Projects found")
            return
        
        print(f"\n✅ Found {len(projects)} project(s):\n")
        print(f"{'Number':<8} {'ID':<30} {'Title'}")
        print("-" * 70)
        
        for proj in projects:
            number = proj.get('number', 'N/A')
            proj_id = proj.get('id', 'N/A')[:27] + "..." if len(proj.get('id', '')) > 30 else proj.get('id', 'N/A')
            title = proj.get('title', 'Untitled')
            print(f"#{number:<7} {proj_id:<30} {title}")
        
        print("\n💡 Copy the Project Number and Project ID above")
        print("   Then use option [5] 🐙 GitHub Project (Kanban) to configure")
        
    except FileNotFoundError:
        print("❌ GitHub CLI (gh) not found")
        print("\n💡 Install with: brew install gh")
        print("   Then authenticate: gh auth login")
    except subprocess.TimeoutExpired:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")


def _edit_github_project():
    """Sub-menu to edit GitHub Project (Kanban) info for projects."""
    from luma_core.config import (
        load_projects,
        save_projects,
        PROJECTS,
    )
    
    print("\n🐙 Edit GitHub Project (Kanban) Settings")
    print("=" * 50)
    
    # Show all projects
    projects = load_projects()
    if not projects:
        print("❌ No projects found")
        return
    
    print("\nAvailable projects:")
    project_keys = sorted(projects.keys(), key=lambda k: int(k) if k.isdigit() else k)
    for i, key in enumerate(project_keys, 1):
        proj = projects[key]
        kanban = proj.get("kanban_number")
        kanban_str = f"Project #{kanban}" if kanban else "Not configured"
        print(f"  [{i}] {proj['name']} ({key}) - {kanban_str}")
    print("  [0] Cancel")
    print("  [type 'list' or 'help' to show GitHub Projects from API]")
    
    while True:
        choice = safe_input("\nSelect project to edit: ").strip().lower()
        
        if choice == "0" or not choice:
            return
        
        if choice in ("list", "help", "l", "h"):
            _list_github_projects()
            # After listing, show the menu again
            print("\n" + "=" * 50)
            print("\nAvailable projects:")
            for i, key in enumerate(project_keys, 1):
                proj = projects[key]
                kanban = proj.get("kanban_number")
                kanban_str = f"Project #{kanban}" if kanban else "Not configured"
                print(f"  [{i}] {proj['name']} ({key}) - {kanban_str}")
            print("  [0] Cancel")
            print("  [type 'list' or 'help' to show GitHub Projects from API]")
            continue
        
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(project_keys):
                print("❌ Invalid selection")
                continue
            selected_key = project_keys[idx]
            break
        except ValueError:
            print("❌ Invalid input. Please enter a number, 'list', or 'help'.")
            continue
    
    selected_project = projects[selected_key]
    print(f"\nEditing: {selected_project['name']}")
    print(f"Path: {selected_project.get('path', 'N/A')}")
    
    current_kanban = selected_project.get("kanban_number")
    if current_kanban:
        print(f"Current GitHub Project: #{current_kanban}")
    else:
        print("Current GitHub Project: Not configured")
    
    print("\n💡 Hint: GitHub Project Number vs Project ID")
    print("   • Project Number = เลขใน URL (เช่น github.com/users/oatrice/projects/12 → 12)")
    print("   • Project ID = GraphQL Node ID สำหรับ API (เช่น PVT_kwHOATfKEM4...)")
    print("   • Type 'list' or 'help' to fetch projects from GitHub API")
    
    while True:
        new_kanban_str = safe_input("\nEnter GitHub Project number (or press Enter to keep current, 'list' for help): ").strip().lower()
        
        if new_kanban_str in ("list", "help", "l", "h"):
            _list_github_projects()
            print("\n" + "-" * 50)
            print(f"\nEditing: {selected_project['name']}")
            print(f"Path: {selected_project.get('path', 'N/A')}")
            current_kanban = selected_project.get("kanban_number")
            if current_kanban:
                print(f"Current GitHub Project: #{current_kanban}")
            else:
                print("Current GitHub Project: Not configured")
            continue
        
        if not new_kanban_str:
            print("ℹ️  No changes made")
            return
        
        try:
            new_kanban = int(new_kanban_str)
            break
        except ValueError:
            print("❌ Invalid number. Please enter a number or type 'list'/'help'.")
            continue
    
    print("\n💡 Hint: Project ID ใช้สำหรับ sync status กับ GitHub (ถ้าไม่มี API จะ sync ไม่ได้)")
    new_kanban_id = safe_input("Enter GitHub Project ID (optional, press Enter to skip): ").strip() or None
    
    # Update project
    selected_project["kanban_number"] = new_kanban
    if new_kanban_id:
        selected_project["kanban_id"] = new_kanban_id
    
    if save_projects(projects):
        print(f"✅ Updated '{selected_project['name']}' with GitHub Project #{new_kanban}")
        # Update PROJECTS in memory directly (for immediate effect in current session)
        import luma_core.config
        luma_core.config.PROJECTS[selected_key] = selected_project
        print(f"   In-memory PROJECTS updated for key '{selected_key}'")
    else:
        print("❌ Failed to save changes")


def action_settings():
    """Settings menu to configure LLM Provider, Agent CLI, Gemini CLI Model, Export Prompts, and GitHub Projects"""
    import json
    import os

    from luma_core.config import (
        AGENT_CLI,
        AVAILABLE_GEMINI_CLI_MODELS,
        GEMINI_CLI_MODEL,
        GLOBAL_CONFIG_FILE,
        LLM_PROVIDER,
        LUMA_EXPORT_PROMPTS,
        normalize_llm_provider,
        save_fallback_index,
        save_gemini_cli_model,
    )

    print("\n⚙️  Settings")
    print("==========")

    # Load current config
    current_config = {}
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                current_config = json.load(f)
        except Exception:
            pass

    current_llm = normalize_llm_provider(current_config.get("LLM_PROVIDER", LLM_PROVIDER))
    original_llm = current_llm
    current_cli = current_config.get("AGENT_CLI", AGENT_CLI)
    current_model = current_config.get("GEMINI_CLI_MODEL", GEMINI_CLI_MODEL)
    # Get export prompts from config, or use current module default (True)
    current_export = current_config.get("LUMA_EXPORT_PROMPTS")
    if current_export is None:
        current_export = LUMA_EXPORT_PROMPTS if LUMA_EXPORT_PROMPTS is not None else True

    while True:
        export_status = "✅ ON (Export prompts to files)" if current_export else "❌ OFF (Call LLM directly)"
        print("\nCurrent Configuration:")
        print(f"  [1] LLM Provider:      {current_llm}")
        print(f"  [2] Agent CLI:         {current_cli}")
        print(f"  [3] Gemini CLI Model:  {current_model}")
        print(f"  [4] Export Prompts:    {export_status}")
        print("  [5] 🐙 Edit GitHub Project (Kanban)")
        print("  [6] � List GitHub Projects (from API)")
        print("  [7] �� Back")

        choice = safe_input("\nSelect setting to change [1-7]: ")

        if choice == "1":
            print("\nSelect LLM Provider:")
            print("  [1] gemini (API)")
            print("  [2] openrouter")
            print("  [3] gemini-cli (Local CLI)")
            print("  [4] codex-cli (Local CLI)")

            p_choice = safe_input("Select [1-4]: ")
            if p_choice == "1":
                current_llm = "gemini"
            elif p_choice == "2":
                current_llm = "openrouter"
            elif p_choice == "3":
                current_llm = "gemini-cli"
            elif p_choice == "4":
                current_llm = "codex-cli"

        elif choice == "2":
            print("\nSelect Agent CLI:")
            print("  [1] gemini_cli")
            print("  [2] opencode")

            c_choice = safe_input("Select [1-2]: ")
            if c_choice == "1":
                current_cli = "gemini_cli"
            elif c_choice == "2":
                current_cli = "opencode"

        elif choice == "3":
            print("\nSelect Gemini CLI Model:")
            for i, model in enumerate(AVAILABLE_GEMINI_CLI_MODELS, 1):
                marker = " ← current" if model == current_model else ""
                print(f"  [{i}] {model}{marker}")

            m_choice = safe_input(f"Select [1-{len(AVAILABLE_GEMINI_CLI_MODELS)}]: ")
            try:
                idx = int(m_choice) - 1
                if 0 <= idx < len(AVAILABLE_GEMINI_CLI_MODELS):
                    current_model = AVAILABLE_GEMINI_CLI_MODELS[idx]
                    save_gemini_cli_model(current_model)
                    print(f"  ✅ Model set to: {current_model}")
                else:
                    print("❌ Invalid option")
            except ValueError:
                print("❌ Invalid option")

        elif choice == "4":
            current_export = not current_export
            status_msg = "ENABLED" if current_export else "DISABLED"
            print(f"\n  🔄 Export Prompts {status_msg}")

        elif choice == "5":
            _edit_github_project()

        elif choice == "6":
            _list_github_projects()

        elif choice == "7" or choice == "":
            break
        else:
            print("❌ Invalid option")

    # Save back to config
    current_config["LLM_PROVIDER"] = current_llm
    current_config["AGENT_CLI"] = current_cli
    current_config["LUMA_EXPORT_PROMPTS"] = current_export

    try:
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)

        if current_llm != original_llm:
            save_fallback_index(0, os.getcwd())

        # Hot-reload config module so get_llm picks up the change immediately
        import importlib

        import luma_core.config

        importlib.reload(luma_core.config)

        print("\n✅ Settings saved!")
    except Exception as e:
        print(f"\n❌ Failed to save settings: {e}")

def action_archive_artifacts(state: LumaState, project: dict, headless: bool = False):
    """Move active artifacts to feature directory"""
    if not state.active_issue:
        if not headless:
            print("❌ No active issue to archive for.")
        return

    combined_number = "-".join([str(i.number) for i in state.active_issues])
    print(f"\n📦 Archiving artifacts for Issue #{combined_number}...")

    # Determine Feature Directory
    # Strategy: Try to find existing dir matching issue number
    features_root = os.path.join(resolve_project_target_dir(project["path"]), "docs", "features")
    if not os.path.exists(features_root):
        os.makedirs(features_root)

    feature_dir = None

    # 1. Check if we already have a context
    if state.context.get("last_feature_dir"):
        feature_dir = state.context.get("last_feature_dir")

    # 2. Search existing
    if not feature_dir:
        for d in os.listdir(features_root):
            if d.startswith(f"{combined_number}_") or f"issue-{combined_number}" in d:
                feature_dir = os.path.join(features_root, d)
                break

    # 3. Create new if needed
    if not feature_dir:
        combined_title = " & ".join([i.title for i in state.active_issues])
        slug = (
            combined_title.lower()
            .replace(" ", "-")
            .replace("[", "")
            .replace("]", "")[:50]
        )
        dirname = f"{combined_number}_{slug}"
        feature_dir = os.path.join(features_root, dirname)
        os.makedirs(feature_dir, exist_ok=True)
        print(f"   📂 Created feature dir: {dirname}")
    else:
        print(f"   📂 Target: {os.path.basename(feature_dir)}")

    # Only archive locally generated planning/documentation artifacts.
    # AI Brain artifacts (task.md, walkthrough.md, etc.) are handled by ai_brain_sync.py
    # and placed in the ai_brain/ subdirectory.
    search_dirs = [resolve_project_target_dir(project["path"])]

    artifacts = ["analysis.md", "spec.md", "plan.md", "sbe.md", "code_review.md"]
    # Also support platform specific variations like plan_android.md
    artifacts = [
        "analysis.md",
        "spec.md",
        "plan.md",
        "sbe.md",
        "plan_android.md",
        "plan_ios.md",
    ]

    moved_count = 0

    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for filename in os.listdir(sdir):
            is_match = filename in artifacts
            if not is_match:
                if filename.startswith("plan_") and filename.endswith(".md"):
                    is_match = True
                if filename.startswith("spec_") and filename.endswith(".md"):
                    is_match = True

            if is_match:
                src = os.path.join(sdir, filename)
                dst = os.path.join(feature_dir, filename)
                try:
                    shutil.move(src, dst)
                    print(f"   ➡️  Moved {filename}")
                    moved_count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to process {filename}: {e}")

    if moved_count == 0:
        print("   (No local artifacts found to archive)")
    else:
        print(f"✅ Archived {moved_count} local files.")

    # 4. Sync AI Brain artifacts (Antigravity & Gemini CLI)
    try:
        from luma_core.ai_brain_sync import AntigravityBrain, GeminiCLIBrain

        # Issue number requires int
        issue_num_int = (
            int(combined_number.split("-")[0])
            if "-" in combined_number
            else int(combined_number)
        )

        # Sync Antigravity
        antigravity_files = AntigravityBrain.sync_to_repo(
            resolve_project_target_dir(project["path"]), issue_num_int
        )
        if antigravity_files:
            print(f"✅ Synced {len(antigravity_files)} Antigravity artifacts.")

        # Sync Gemini CLI
        gemini_files = GeminiCLIBrain.sync_to_repo(resolve_project_target_dir(project["path"]), issue_num_int)
        if gemini_files:
            print(f"✅ Synced {len(gemini_files)} Gemini CLI artifacts.")

    except Exception as e:
        print(f"   ⚠️  Failed to sync AI Brain artifacts: {e}")
