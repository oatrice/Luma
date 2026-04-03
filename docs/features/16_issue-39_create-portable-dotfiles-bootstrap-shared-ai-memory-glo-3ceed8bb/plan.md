```markdown
# Implementation Plan: Create portable dotfiles bootstrap for shared AI memory and global agents

> **Refers to**: Specification for "Create portable dotfiles bootstrap for shared AI memory and global agents"
> **Status**: Draft

## 1. Architecture & Design

### Component View
- **New Components**:
    - A conceptual `dotfiles-repo` (a separate Git repository) containing:
        - `README.md`: Documentation for setup and usage.
        - `bootstrap.py`: Script to install/update AI configuration files in the user's home directory.
        - `capture.py`: Script to synchronize local changes back to the dotfiles repository.
        - `.ai-shared-memory.md`: Template for shared AI memory.
        - `.codex/AGENTS.md`: Template for Codex agent rules.
        - `.gemini/GEMINI.md`: Template for Gemini agent rules.
- **Modified Components (within Luma project)**:
    - `luma_core/project_context.py`: To ensure it correctly resolves paths to AI configuration files using portable home directory references.
    - Potentially other files in `luma_core/agents/` or `luma_core/config.py` if they directly load or reference these AI configuration files with non-portable paths.
- **Dependencies**:
    - Standard Python libraries (`os`, `pathlib`, `shutil`, `subprocess`).
    - Git CLI (for cloning the `dotfiles-repo` and potentially for backup/diffing in `capture.py`).
    - Python 3.9+

### Data Model Changes
No new data structures or database schema changes are anticipated for this feature. The focus is on file management and path resolution.

---

## 2. Step-by-Step Implementation

### Step 1: Create `dotfiles-repo` structure and placeholder content.
- **Objective**: Define the template for portable AI configuration files, ensuring consistency and adherence to project conventions.
- **Action**:
    1.  Establish the directory structure for a new Git repository (`dotfiles-repo`).
    2.  Create the following files within this repository:
        *   `.ai-shared-memory.md`: Populate with basic markdown structure and placeholder content for shared AI memory.
        *   `.codex/AGENTS.md`: Create the `.codex` directory and add `AGENTS.md`. Populate with placeholder agent rules, ensuring any references to shared memory use portable paths (e.g., `source: ~/.ai-shared-memory.md`).
        *   `.gemini/GEMINI.md`: Create the `.gemini` directory and add `GEMINI.md`. Populate with placeholder agent rules, similar to `.codex/AGENTS.md`, ensuring portable path references.
    3.  Ensure all file paths within these placeholder files correctly use the `~` or `$HOME` syntax for portability.
- **Files**:
    *   `dotfiles-repo/.ai-shared-memory.md`
    *   `dotfiles-repo/.codex/AGENTS.md`
    *   `dotfiles-repo/.gemini/GEMINI.md`
- **Verification**: Manually review the created files within the conceptual `dotfiles-repo` to confirm correct structure and the use of portable home directory references for all internal paths.

### Step 2: Develop `bootstrap.py` script.
- **Objective**: Create a script to automate the installation and setup of AI configuration files from the `dotfiles-repo` to the user's home directory.
- **Action**:
    1.  Create a Python script named `bootstrap.py` in the root of the `dotfiles-repo`.
    2.  Implement logic within `bootstrap.py` to:
        *   Determine the path to the `dotfiles-repo` (e.g., by looking at the current working directory).
        *   Define the target installation paths in the user's home directory (e.g., `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`).
        *   Copy or create symbolic links for the configuration files from the `dotfiles-repo` to their respective target locations.
        *   Include robust error handling and user prompts for cases where target files already exist (e.g., prompt for overwrite, update symlinks, or skip).
        *   Ensure that the script correctly resolves and applies portable paths within the files it manages.
- **Files**: `dotfiles-repo/bootstrap.py`
- **Verification**: In a simulated environment, clone the `dotfiles-repo`, execute `bootstrap.py`, and verify that the AI configuration files are correctly created or linked in the user's home directory, and that all internal paths are portable.

### Step 3: Develop `capture.py` script.
- **Objective**: Create a script to synchronize local changes made in the user's home directory back to the `dotfiles-repo`.
- **Action**:
    1.  Create a Python script named `capture.py` in the root of the `dotfiles-repo`.
    2.  Implement logic within `capture.py` to:
        *   Identify the location of the `dotfiles-repo`.
        *   Locate the user's AI configuration files in their home directory.
        *   Copy the content from these local home directory files back to their corresponding locations within the `dotfiles-repo`.
        *   Implement safety measures to prevent accidental data loss, such as performing a diff or creating a backup of the repository files before overwriting them.
- **Files**: `dotfiles-repo/capture.py`
- **Verification**: In a test setup, perform the bootstrap process, make a manual modification to a configuration file in the user's home directory, then run `capture.py` from the `dotfiles-repo`. Verify that the changes are correctly synchronized back into the `dotfiles-repo`.

### Step 4: Update Luma Core to use portable AI configuration paths.
- **Objective**: Ensure that Luma's agents and core logic correctly locate and use AI configuration files via portable paths, regardless of where the `dotfiles-repo` is cloned.
- **Action**:
    1.  Analyze the Luma project's codebase, focusing on `luma_core/project_context.py` and any other relevant files (e.g., in `luma_core/agents/` or `luma_core/config.py`) that are responsible for loading AI configuration files or project context.
    2.  Identify any hardcoded or non-portable paths used to access files like `.ai-shared-memory.md` or agent rule files.
    3.  Modify these references to use portable path resolution mechanisms, such as `os.path.expanduser('~')` or `pathlib.Path.home()`, to dynamically locate these files.
- **Files**: `luma_core/project_context.py` (and potentially other files in `luma_core/agents/` or `luma_core/config.py`).
- **Verification**: Run all existing unit and integration tests within the Luma project that pertain to AI configuration loading, agent initialization, or project context setup. Ensure these tests pass when the AI configuration files are managed by the bootstrapped `dotfiles-repo`.

### Step 5: Document the `dotfiles-repo` setup and capture process.
- **Objective**: Provide clear and comprehensive instructions for users to adopt and utilize the portable dotfiles system.
- **Action**:
    1.  Create a `README.md` file in the root directory of the `dotfiles-repo`.
    2.  Populate the `README.md` with the following sections:
        *   **Introduction**: Briefly explain the purpose and benefits of the portable dotfiles.
        *   **Prerequisites**: List necessary software (e.g., Git, Python 3.9+).
        *   **Setup (Bootstrap)**: Provide step-by-step instructions on how to clone the `dotfiles-repo` and run the `bootstrap.py` script.
        *   **Usage (Capture)**: Explain how to use the `capture.py` script to synchronize local changes back to the repository.
        *   **Troubleshooting**: Include common issues and their resolutions.
- **Files**: `dotfiles-repo/README.md`
- **Verification**: Review the `README.md` for clarity, accuracy, completeness, and ease of understanding. Ensure all instructions are actionable.

### Step 6: Ensure Preservation of Cross-vendor Rules and Conventions.
- **Objective**: Maintain existing cross-vendor rules (e.g., rebase conflict handling, release versioning) and Luma's internal conventions within the new portable setup.
- **Action**:
    1.  Review the placeholder content created in Step 1 for `.codex/AGENTS.md` and `.gemini/GEMINI.md` to ensure that the established cross-vendor rules (rebase conflict handling, release versioning) are correctly included or referenced.
    2.  Verify that the modifications made to Luma Core in Step 4 ensure these rules are correctly parsed and applied from the portable paths.
- **Files**: Primarily affects the content of `dotfiles-repo/.codex/AGENTS.md`, `dotfiles-repo/.gemini/GEMINI.md`, and the agent loading logic within Luma Core.
- **Verification**: After bootstrapping the system using the new dotfiles, manually confirm that the cross-vendor rules are present and functional within Luma's agents, preserving the intended behavior.

---

## 3. Verification Plan

### Automated Tests
- **`dotfiles-repo`**:
    - Unit tests for `bootstrap.py` (e.g., testing file copying, symlinking, path resolution, existing file handling).
    - Unit tests for `capture.py` (e.g., testing file synchronization, backup logic, path resolution).
    - These tests would reside within a `tests/` directory inside the `dotfiles-repo`.
- **Luma Project**:
    - Execute all existing unit and integration tests in the Luma project that cover AI configuration loading, agent initialization, and project context management. Ensure all tests related to these functionalities pass after Step 4 is implemented.

### Manual Verification
- **New Machine Setup Simulation**:
    1.  Clone the `dotfiles-repo` to a clean directory.
    2.  Run `python bootstrap.py` from within the cloned repository.
    3.  Verify that `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, and `~/.gemini/GEMINI.md` are created/linked correctly in the home directory.
    4.  Inspect the content of these files to ensure portable paths are used.
- **Local Changes Synchronization**:
    1.  Modify one of the AI configuration files in the home directory (e.g., add a note to `~/.ai-shared-memory.md`).
    2.  Navigate to the `dotfiles-repo` directory.
    3.  Run `python capture.py`.
    4.  Verify that the corresponding file within the `dotfiles-repo` has been updated with the local changes.
- **Luma Agent Functionality**:
    1.  Ensure Luma agents can load and use the AI configuration and shared memory as expected after bootstrapping.
    2.  Confirm that cross-vendor rules (rebase conflict handling, release versioning) are correctly interpreted and applied by the agents.
- **Documentation Review**:
    1.  Read through the `dotfiles-repo/README.md` to ensure it is clear, accurate, and easy to follow.
```