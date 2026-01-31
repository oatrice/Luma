# Luma Verification Master Plan

This document outlines the strategy to verify the Luma Workflow Guardian across all implemented phases (1-6).

## 1. Functional Testing

### Phase 1: State Management (Core)
*   **Goal**: Ensure state transitions are valid and persistence works.
*   **Automated Verification**:
    ```bash
    PYTHONPATH=. pytest tests/test_state_manager.py
    ```
*   **Manual Check**:
    1. Run `python3 main.py`
    2. Start a task -> Check `.luma_state.json` updates to `coding`.
    3. Finish task -> Check `.luma_state.json` updates to `pr_pending` or `idle`.

### Phase 2: GitHub Integration
*   **Goal**: specific GitHub connectivity and Kanban sync.
*   **Automated Verification** (Mocked):
    ```bash
    PYTHONPATH=. pytest tests/test_github_project.py
    ```
*   **Manual Check**:
    1. Run `python3 main.py`.
    2. Select an issue from the list (Requires real GH_TOKEN).
    3. Verify the issue moves to "In Progress" on the GitHub Project Board.

### Phase 3: Pre-flight Checker
*   **Goal**: Verify rules block invalid states.
*   **Automated Verification**:
    ```bash
    PYTHONPATH=. pytest tests/test_preflight.py
    ```
*   **Manual Check**:
    1. Setup a dummy rule in `.luma_rules.json` that requires a file `REQUIRED_FILE`.
    2. Try to run a "Submit PR" action without creating the file.
    3. Verify Luma blocks the action with an error.

### Phase 4: Context Summarizer
*   **Goal**: Verify correct context is shown.
*   **Automated Verification**:
    ```bash
    PYTHONPATH=. pytest tests/test_context_summarizer.py
    ```
*   **Manual Check**:
    1. Open a task associated with `JarWise-Android`.
    2. Verify the "Context" section in Luma CLI displays Android-specific rules (e.g., "Follow Material Design 3").

### Phase 5: UI Upgrade
*   **Goal**: Visual regression testing.
*   **Automated Verification**: N/A (UI logic is tied to main loop, hard to unit test visually).
*   **Manual Check**:
    1. Observe the header: Is it colored? (Blue for Idle, Green for Coding).
    2. Are emojis displayed correctly?
    3. Does the screen clear properly between transitions?

### Phase 6: Project Configuration
*   **Goal**: Verify configuration loading and validation.
*   **Automated Verification**:
    ```bash
    PYTHONPATH=. python3 tests/verify_phase6.py
    PYTHONPATH=. pytest tests/test_rules_loader.py
    ```

## 2. Non-Functional Testing

### Performance
*   **Startup Time**: Run `time python3 main.py --help`. Should be < 1s.
*   **API Latency**: GitHub fetches should be cached or async where possible (currently synchronous, check if waiting time is acceptable < 3s).

### Usability
*   **Error Messages**: triggers faults (e.g., disconnect internet) and check if Luma crashes gracefully or shows a stack trace.
*   **Keyboard Interrupt**: Press `Ctrl+C` during any operation. Luma should exit cleanly without corrupting `.luma_state.json`.

### Compatibility
*   **Multi-Platform Configuration**:
    * Run Luma from `JarWise-Root`.
    * Run Luma from `JarWise-Web`.
    * Verify it loads the correct `.luma_rules.json` for each directory.

## 3. Full Regression Suite Command

To run all automated tests at once:

```bash
PYTHONPATH=. pytest tests/
```
