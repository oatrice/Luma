# Implementation Plan: Add Headless CLI Contract for External Callers

> **Refers to**: Spec: Add Headless CLI Contract for External Callers
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `main.py`: To integrate `argparse` for new arguments (`--auto`, `--action`, `--json`, `--project`), and to orchestrate the headless execution flow.
    - `luma_core/tools.py` (or a new utility module): To potentially house utility functions for JSON serialization, error wrapping, and action mapping.
- **New Components**:
    - A dedicated function within `main.py` or `luma_core/tools.py` to handle the headless execution logic, including argument parsing, action dispatching, JSON formatting, and exit code management.
- **Dependencies**:
    - `argparse` (built-in Python library) for command-line argument parsing.
    - `json` (built-in Python library) for JSON serialization.
    - `sys` (built-in Python library) for managing `sys.exit`.

### Data Model Changes
No new data models are introduced. The output will be in JSON format with a defined structure for success and error cases.

---

## 2. Step-by-Step Implementation

### Step 1: Enhance Argument Parsing in `main.py`
- **Docs**: Update `README.md` or create a dedicated `CLI_CONTRACT.md` to document the new arguments and their usage.
- **Code**: Modify `main.py` to add `--auto`, `--action`, `--json`, and `--project` as arguments to the `ArgumentParser`. Define appropriate help messages and types. Ensure these arguments can coexist with existing interactive CLI functionality.
- **Tests**: Add unit tests in `tests/test_main.py` to verify that `argparse` correctly parses these new arguments and that they are accessible.

### Step 2: Centralize Action Mapping and Execution
- **Docs**: No new documentation files.
- **Code**: Create a function (e.g., `_execute_headless_action`) within `main.py` or `luma_core/tools.py`. This function will:
    - Take the parsed arguments as input.
    - Map the `--action` string provided to the corresponding function in `luma_core/actions`. This mapping could be a dictionary or a lookup mechanism.
    - Handle cases where the action name is not found by returning a specific error object or raising a custom exception (e.g., `ActionNotFoundError`).
    - Execute the mapped action, passing necessary arguments like `--project`.
    - Return the result of the action or propagate any exceptions raised.
- **Tests**: Add unit tests for this action mapping and execution function. Mock the `luma_core.actions` module to ensure correct function calls are made and that appropriate errors are handled for invalid action names.

### Step 3: Implement JSON Output and Error Formatting
- **Docs**: Update the documentation to specify the JSON schema for success and error responses.
- **Code**: Extend the `_execute_headless_action` function or create a new wrapper function in `main.py`.
    - If the `--json` flag is present:
        - Wrap the action execution logic within a `try-except` block.
        - On successful execution, construct a Python dictionary for JSON output: `{"status": "success", "action": action_name, "project": project_key, "result": action_result}`.
        - On caught exceptions (e.g., `ActionNotFoundError`, general execution errors), construct a Python dictionary for error JSON output: `{"status": "error", "action": action_name, "project": project_key, "error": error_message}`.
        - Use `json.dumps()` to serialize the dictionary to a JSON string.
        - Print the JSON string to `sys.stdout`.
- **Tests**: Add unit tests to verify the JSON output structure for both success and error scenarios, ensuring all required fields are present and correctly populated.

### Step 4: Implement Consistent Exit Codes
- **Docs**: Clearly define and document the non-zero exit codes for different error types in the CLI contract documentation.
- **Code**: In `main.py`, when the `--json` flag is active:
    - If an error occurs (e.g., unknown action, exception during execution), call `sys.exit(non_zero_code)`. Define specific codes (e.g., `1` for unknown action, `2` for other execution errors).
    - If execution is successful, call `sys.exit(0)`.
- **Tests**: Add tests to verify that `sys.exit()` is called with the correct exit codes under different error conditions when `--json` is enabled.

### Step 5: Create Headless CLI Contract Documentation
- **Docs**: Create a new file, e.g., `docs/HEADLESS_CONTRACT.md`, or update the `README.md`'s usage section. This documentation must include:
    - A detailed description of the new headless arguments (`--auto`, `--action`, `--json`, `--project`).
    - The precise JSON schema for both success and error responses.
    - An explanation of the exit codes used by the CLI in headless mode.
- **Code**: No code changes are needed for this step; it's purely documentation.
- **Tests**: No automated tests, but manual review of the documentation by a peer for clarity, completeness, and accuracy.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- **Unit Tests (`tests/test_main.py` and potentially new test files for helpers):**
    - Verify that `argparse` correctly parses the new `--auto`, `--action`, `--json`, and `--project` arguments.
    - Test the action mapping mechanism, ensuring that the correct internal action functions are called and that appropriate errors are raised or returned for invalid action names.
    - Test the JSON output generation for success cases, confirming the structure and content of the `result` field.
    - Test the JSON output generation for error cases, ensuring the `error` message and structure conform to the defined schema.
    - Verify that `sys.exit()` is called with the correct exit codes (0 for success, non-zero for errors) when the `--json` flag is active.
- **Integration Tests**:
    - Write integration tests that simulate executing `main.py` with the new headless arguments.
    - Assert the captured `stdout` (JSON content), `stderr`, and `sys.exit_code` against expectations.
    - Utilize the Specification's SBE examples as primary test cases for these integration tests.

### Manual Verification
- Execute the exact command-line examples provided in the Specification's SBE section directly in the terminal. Confirm that the printed JSON output and the command's exit code match the expected values precisely.
- Test the scenario of invoking the CLI with an unrecognized `--action` name to verify that the JSON error output is correctly formatted and that a non-zero exit code is returned.
- Manually trigger an internal error within a known action (e.g., by providing invalid input to the action that is known to cause it to fail) to confirm that the error JSON structure and appropriate exit code are produced.
- Test the CLI with unrecognized command-line flags to ensure that the usage message is displayed on `stderr` and a non-zero exit code is returned, confirming robustness against invalid arguments.