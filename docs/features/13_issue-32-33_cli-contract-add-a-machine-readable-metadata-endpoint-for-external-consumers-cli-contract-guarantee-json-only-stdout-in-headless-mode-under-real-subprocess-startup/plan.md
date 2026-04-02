# Implementation Plan: CLI Contract: Metadata Endpoint and Headless JSON Output Guarantees

> **Refers to**: ./spec.md
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `main.py`: To parse new `--meta --json` CLI flags and manage output streams to stdout/stderr.
    - `luma_core/config.py`: To define `CONTRACT_VERSION` and `SUPPORTED_ACTIONS`.
    - `luma_core/tools.py`: To house utility functions for retrieving version, git info, Python version, and orchestrating metadata assembly.
    - `luma_core/ui.py` / `main.py`: Logic to ensure strict stdout/stderr separation for metadata output.
- **New Components**:
    - A new function `get_metadata()` in `luma_core/tools.py` to collect all metadata.
    - CLI argument parsing and output handling logic within `main.py`.
- **Dependencies**:
    - Standard Python libraries: `sys`, `subprocess`, `json`.
    - Project internal modules/files: `luma_core/config.py`, `VERSION` file.

---

## 2. Step-by-Step Implementation

### Step 1: Define Contract Version and Supported Actions
- **Docs**: N/A (Internal configuration).
- **Code**: Add `CONTRACT_VERSION = "v1"` and `SUPPORTED_ACTIONS = ["analyze", "plan", "code", "review"]` as constants to `luma_core/config.py`.
- **Tests**: N/A.

### Step 2: Implement Metadata Retrieval Utilities
- **Docs**: Add comprehensive docstrings to new functions within `luma_core/tools.py` explaining their purpose, arguments, and return values.
- **Code**:
    - Create `luma_core/tools.py` if it does not exist.
    - Implement `get_luma_version()`: Reads and returns the content of the `VERSION` file.
    - Implement `get_git_info()`: Utilizes `subprocess` to execute `git rev-parse HEAD` and `git status --porcelain`. This function will return a tuple `(commit_hash, is_dirty)`. It must gracefully handle cases where Luma is not installed in a Git repository by returning `(None, None)`.
    - Implement `get_python_version()`: Returns the current Python version string using `sys.version_info` (e.g., "3.9.18").
    - Implement `get_metadata()`: This function will orchestrate calls to the above utility functions and retrieve `CONTRACT_VERSION` and `SUPPORTED_ACTIONS` from `luma_core.config`. It will return a dictionary containing `version`, `git_commit`, `dirty`, `contract_version`, `supported_actions`, and `python_version`.
- **Tests**: Write unit tests in a new or existing test file (e.g., `tests/test_tools.py`) for `get_luma_version`, `get_git_info` (mocking `subprocess` for various scenarios including non-Git repos), and `get_python_version`.

### Step 3: Integrate Metadata Endpoint into CLI
- **Docs**: Update CLI help messages in `main.py`'s argument parser to reflect the new `--meta --json` options.
- **Code**:
    - In `main.py`, modify the argument parsing logic to accept and recognize `--meta` and `--json` flags.
    - Implement conditional logic: If both `--meta` and `--json` flags are present, call the `get_metadata()` function.
    - Serialize the returned metadata dictionary into a JSON string using `json.dumps()`.
    - Ensure this JSON string is printed *exclusively* to `sys.stdout`.
    - Implement mechanisms to redirect all other diagnostic `print` statements or logging output to `sys.stderr` when the `--meta --json` flags are active, guaranteeing a clean stdout.
    - The program should exit cleanly after printing the metadata.
- **Tests**: Add unit tests in `tests/test_main.py` to verify:
    - The correct JSON payload is emitted to `stdout` when `python main.py --meta --json` is called.
    - `stdout` remains clean and contains only the JSON output.
    - Diagnostic messages (simulated warnings/info) are correctly directed to `stderr`.
    - The `git_commit` and `dirty` fields in the output are correctly set to `None` when the environment is not a Git repository.

### Step 4: Update Documentation
- **Docs**: Add a new section to the project's `README.md` (or a dedicated CLI documentation file, if applicable) that details the new `--meta --json` command. This documentation should describe:
    - The command's purpose.
    - Its arguments.
    - The structure of the JSON payload, including a description of each field (`version`, `git_commit`, `dirty`, `contract_version`, `supported_actions`, `python_version`).
    - The behavior regarding stdout/stderr stream separation.
- **Code**: N/A.
- **Tests**: N/A.

### Step 5: Comprehensive Unit Testing
- **Docs**: N/A.
- **Code**: Implement all necessary unit tests as detailed in Steps 2 and 3. Ensure that test coverage is comprehensive, including:
    - Happy path scenarios with valid inputs.
    - Edge cases such as an empty `VERSION` file, missing `git` executable, or an invalid Git repository structure.
    - Verification of the non-Git repository scenario handling.
- **Tests**: N/A.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- **Unit Tests**:
    - Tests for `luma_core/tools.py` covering `get_luma_version`, `get_git_info` (with mocked `subprocess` for Git and non-Git scenarios), `get_python_version`, and the combined `get_metadata` function.
    - Tests for `main.py` to validate CLI argument parsing, the correct invocation of metadata generation, and the accuracy and stream separation of the command's output.
- **Integration Tests**: (Optional, but recommended) If applicable, tests that simulate running `main.py` as a subprocess and capturing its stdout/stderr.

### Manual Verification
- **Checklist**:
    - Execute `python main.py --meta --json` in a clean, active Git repository. Verify that `stdout` contains a correctly formatted JSON object with accurate `version`, `git_commit`, `dirty: false`, `contract_version`, `supported_actions`, and `python_version`.
    - Execute `python main.py --meta --json` in a directory that is *not* a Git repository. Verify that `git_commit` and `dirty` fields are `null`, and a warning message is present on `stderr`.
    - Introduce temporary diagnostic `print` statements (that would normally go to stdout) in other parts of the codebase. Run `python main.py --meta --json` and confirm these messages appear on `stderr` and not `stdout`.
    - Verify that the `supported_actions` and `contract_version` in the JSON output precisely match the values defined in `luma_core/config.py`.