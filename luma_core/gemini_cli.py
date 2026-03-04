import subprocess

def delegate_task_to_gemini(task_file_path: str, project_path: str):
    """
    Delegate a given task file to gemini cli for automated agentic execution.
    """
    try:
        subprocess.run(
            [
                "gemini", 
                "-m", "gemini-2.5-pro",
                "--file", task_file_path,
                "Please read the attached task file and implement the features. Check off tasks as you go."
            ],
            cwd=project_path,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to delegate to gemini cli: {e}")
        raise
