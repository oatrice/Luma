import subprocess

def delegate_task_to_opencode(task_file_path: str, project_path: str):
    """
    Delegate a given task file to opencode for automated agentic execution.
    """
    prompt = "Please read the attached task file and implement the features using TDD (Red -> Green -> Refactor). Check off tasks as you go."
    
    try:
        subprocess.run(
            [
                "opencode", 
                "run", prompt, 
                "--file", task_file_path, 
                "--dir", project_path
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to delegate to opencode: {e}")
        raise
