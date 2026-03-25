import ast
import os

source_file = "luma_core/actions.py"
dest_dir = "luma_core/actions"

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

with open(source_file, "r") as f:
    source = f.read()
    source_lines = source.splitlines()

tree = ast.parse(source)

# Identify different chunks bounds
chunks = []
current_imports = []
current_helpers = []

def get_source_segment(node):
    # Handle the fact that ast nodes might not cover decorators if we just use lineno in python < 3.8
    # But in python 3.8+ node.decorator_list has lineno, however ast.get_source_segment handles it
    return ast.get_source_segment(source, node)

groups = {
    "issue_actions.py": [
        "action_select_issue", "action_add_issue", "action_remove_issue", 
        "action_list_active_issues", "action_view_kanban"
    ],
    "plan_actions.py": [
        "action_generate_sbe", "action_generate_draft", "action_generate_spec", 
        "action_generate_plan", "action_refine_issue"
    ],
    "quality_actions.py": [
        "action_code_review", "action_update_docs", "action_update_roadmap"
    ],
    "workflow_actions.py": [
        "action_create_pr", "action_guided_workflow", "action_run_multi_agent_coding"
    ],
    "admin_actions.py": [
        "action_archive_artifacts", "action_test_telegram_notification", 
        "action_switch_project", "action_settings", "action_sync_ai_brain"
    ],
    "metrics_actions.py": [
        "action_manage_issue_metrics", "action_view_dashboard", 
        "action_generate_project_report", "action_view_stats_files"
    ]
}

# Collect imports
import_nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
import_text = "\n".join([ast.get_source_segment(source, n) for n in import_nodes])

# Collect everything that is not an action_* function
helpers_text = []
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name.startswith("action_"):
        continue
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        continue
    helpers_text.append(ast.get_source_segment(source, n))

helpers_combined = "\n\n".join(helpers_text)

# Write utils.py
utils_path = os.path.join(dest_dir, "utils.py")
with open(utils_path, "w") as f:
    f.write(import_text + "\n\n" + helpers_combined + "\n")

print(f"Created utils.py")

# Function to write each module
def write_module(filename, function_names):
    funcs_text = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in function_names:
            funcs_text.append(ast.get_source_segment(source, n))
    
    if not funcs_text:
        return
        
    path = os.path.join(dest_dir, filename)
    with open(path, "w") as f:
        # Import everything from utils
        f.write("from .utils import *\n\n")
        f.write("\n\n".join(funcs_text) + "\n")
    print(f"Created {filename} with {len(funcs_text)} functions")

for filename, funcs in groups.items():
    write_module(filename, funcs)

# Create __init__.py
init_path = os.path.join(dest_dir, "__init__.py")
with open(init_path, "w") as f:
    for filename in groups.keys():
        mod = filename.replace(".py", "")
        f.write(f"from .{mod} import *\n")
    f.write(f"from .misc_actions import *\n")
    f.write(f"from .utils import *\n")

print("Created __init__.py")

# Create misc_actions.py for any leftover action_ functions
assigned_funcs = set(f for flist in groups.values() for f in flist)
misc_funcs_text = []
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name.startswith("action_") and n.name not in assigned_funcs:
        misc_funcs_text.append(ast.get_source_segment(source, n))

if misc_funcs_text:
    misc_path = os.path.join(dest_dir, "misc_actions.py")
    with open(misc_path, "w") as f:
        f.write("from .utils import *\n\n")
        f.write("\n\n".join(misc_funcs_text) + "\n")
    print(f"Created misc_actions.py with {len(misc_funcs_text)} functions")
print("Refactoring completed. Remember to update main.py or other imports if needed.")
