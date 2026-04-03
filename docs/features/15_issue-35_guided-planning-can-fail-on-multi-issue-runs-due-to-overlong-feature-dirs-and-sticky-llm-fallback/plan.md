```markdown
# Implementation Plan: Guided Planning Reliability for Multi-Issue Runs

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `luma_core/feature_dirs.py`: Responsible for generating feature directory paths. Will be enhanced to handle long titles safely and deterministically.
    - `luma_core/llm.py` (or a related LLM orchestrator module): Contains the logic for invoking LLM models and managing fallback. Will be updated to implement circular fallback.
    - `luma_core/state_manager.py`: Manages the application state, including the saved active LLM fallback position.
    - `luma_core/workflow.py` (or `luma_core/actions/plan_actions.py`): Orchestrates the Guided Planning workflow and integrates the new workspace naming and fallback logic.
- **New Components**:
    - A utility function (e.g., `_generate_safe_dirname_hash`) within `luma_core/feature_dirs.py` or `luma_core/tools.py` to generate a deterministic, short hash for long titles.
- **Dependencies**:
    - Python's `hashlib` for generating deterministic short hashes.
    - Standard `os` or `pathlib` for path manipulation and length checks.

### Data Model Changes
```python
# luma_core/state_manager.py (or LumaState definition)
class LumaState:
    # ... existing fields
    active_llm_fallback_position: int = 0  # New field to store the index of the last successful LLM in the configured chain
                                          # This will be used as the starting point for the next fallback attempt.
```
The `LumaState` object, which persists to `.luma_state.json`, will be updated to include `active_llm_fallback_position` to track the last successful model's index in the fallback chain.

---

## 2. Step-by-Step Implementation

### Step 1: Implement `get_safe_planning_workspace_name` Utility Function
- **Docs**: Add clear docstrings to the new utility function explaining its purpose, parameters, and return value, including how it ensures determinism, traceability, and length safety.
- **Code**:
    1.  Create a new private utility function, e.g., `_generate_safe_dirname_hash(full_title: str) -> str`, within `luma_core/feature_dirs.py` or `luma_core/tools.py`. This function will take the full combined title and return a short, deterministic hash (e.g., a portion of an MD5 or SHA1 hash).
    2.  Implement `get_safe_planning_workspace_name(issue_id: str, combined_title: str) -> str` in `luma_core/feature_dirs.py`. This function will:
        *   Construct the initial basename: `f"{issue_id}_{combined_title}"`.
        *   Check if the full path derived from this basename would exceed typical filesystem limits.
        *   If too long, truncate the `combined_title` portion, ensuring the `issue_id` prefix is always preserved.
        *   Append the result of `_generate_safe_dirname_hash(combined_title)` to the truncated descriptive part to maintain determinism and avoid collisions.
        *   Ensure single-issue titles or short combined titles are not unnecessarily shortened.
- **Tests**:
    *   Create `tests/test_feature_dirs.py` to house new unit tests.
    *   Add unit tests for `get_safe_planning_workspace_name` to verify:
        *   Correct handling of very long combined titles (truncation, hash appending).
        *   Preservation of `issue_id` traceability.
        *   Determinism: the same input always yields the same output.
        *   Compatibility: short titles and single-issue titles remain readable and are not unnecessarily shortened.
        *   Edge cases with titles at or near the length limits.

### Step 2: Integrate Safe Workspace Naming into Guided Planning Workflow
- **Docs**: Update any internal documentation or comments related to planning workspace creation to reference the new utility function.
- **Code**:
    1.  Modify functions in `luma_core/feature_dirs.py` (or other modules responsible for creating/resolving feature directories, potentially `luma_core/actions/plan_actions.py`) to use `get_safe_planning_workspace_name` when generating the directory for planning artifacts.
    2.  Ensure that `Analyst` and `Spec` phases (and subsequent phases like SBE and Architect) consistently call this new function with the same `issue_id` and `combined_title` to guarantee they resolve to and use the identical planning workspace. This likely involves storing the `combined_title` and `issue_id` in the `LumaState` for the current run.
- **Tests**:
    *   Add integration tests in `tests/test_guided_planning_multi_issue.py`.
    *   Simulate a multi-issue Guided Planning run with a very long combined title.
    *   Verify that `analysis.md` and `spec.md` are created within the *same* correctly named, safe directory under `docs/features/`.
    *   Assert that the directory name contains the combined issue ID and a deterministic hash for long titles, or a simple readable name for short titles.

### Step 3: Implement Circular LLM Fallback Logic
- **Docs**: Document the new circular fallback strategy within `luma_core/llm.py` or a dedicated LLM configuration module.
- **Code**:
    1.  Modify `LumaState` (as defined in `luma_core/state_manager.py`) to include `active_llm_fallback_position: int`. Initialize this to `0` if not present.
    2.  In the LLM invocation logic (likely within `luma_core/llm.py`), retrieve the `active_llm_fallback_position` from `LumaState` at the start of a new LLM request.
    3.  When an LLM call fails (e.g., timeout, rate-limit, transient error):
        *   Iterate through the configured LLM models, starting from the `active_llm_fallback_position`.
        *   Implement circular iteration: if the end of the model list is reached, wrap around to the beginning.
        *   Attempt each model sequentially, ensuring each model is tried at most once per full pass.
        *   If a model succeeds, update `active_llm_fallback_position` in `LumaState` to the index of the successful model, and return the successful response.
        *   If all models in the configured chain are attempted (one full circular pass) and all fail, raise a specific exception indicating total fallback exhaustion.
- **Tests**:
    *   Create `tests/test_llm_fallback.py` for new unit tests.
    *   Mock LLM providers to simulate various failure scenarios (transient errors, timeouts, rate limits).
    *   Test cases should include:
        *   Fallback starting from `active_llm_fallback_position = 0`.
        *   Fallback starting from a mid-list `active_llm_fallback_position`.
        *   Fallback successfully wrapping around the list to find a working model.
        *   All models failing after one full circular pass, leading to a total failure.
        *   Verification that `active_llm_fallback_position` is correctly updated upon a successful LLM call.

### Step 4: Integrate Circular Fallback into Guided Planning Workflow
- **Docs**: Update any workflow diagrams or descriptions to reflect the robust LLM fallback mechanism.
- **Code**:
    1.  Ensure all LLM calls within the Guided Planning workflow (Analyst, Spec, SBE, Architect phases, likely coordinated by `luma_core/workflow.py` or `luma_core/actions/plan_actions.py`) correctly utilize the circular fallback mechanism implemented in `luma_core/llm.py`.
    2.  Modify the Guided Planning error handling to catch the specific exception raised when the full fallback chain is exhausted (from Step 3).
    3.  When total fallback exhaustion occurs, gracefully stop the planning handoff, log a clear message about the recovery failure, and report the final planning failure to the user.
    4.  Implement logging to clearly indicate which model succeeded during a fallback attempt and when the full fallback chain was exhausted, satisfying observability requirements.
- **Tests**:
    *   Add integration tests in `tests/test_guided_planning_fallback.py`.
    *   Simulate a complete Guided Planning run where LLM models are configured to fail in a pattern that triggers circular fallback and eventually a successful recovery.
    *   Simulate a complete Guided Planning run where all configured LLM models fail after one full circular pass, verifying that the workflow terminates gracefully with a final failure message.
    *   Verify that the `active_llm_fallback_position` in `LumaState` is correctly updated across planning phases after a successful LLM call.

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [x] Unit Tests:
    - `tests/test_feature_dirs.py`: For `get_safe_planning_workspace_name` utility function to ensure deterministic, traceable, and length-safe directory naming under various title length scenarios (Step 1).
    - `tests/test_llm_fallback.py`: For the circular LLM fallback logic, covering starting positions, successful recovery, and full chain exhaustion scenarios, including `active_llm_fallback_position` updates (Step 3).
- [x] Integration Tests:
    - `tests/test_guided_planning_multi_issue.py`: Verify that Guided Planning with very long combined issue titles consistently creates and reuses the same safe planning workspace across Analyst and Spec phases (Step 2).
    - `tests/test_guided_planning_fallback.py`: Simulate transient LLM failures during a multi-issue planning run to ensure that the circular fallback mechanism correctly recovers and continues the workflow, and that a final failure is reported only when all models are exhausted (Step 4).

### Manual Verification
- [ ] **Long Title Workspace Creation**:
    - Trigger Guided Planning for a set of issues with a very long combined title.
    - Verify that a new directory is created under `docs/features/` with a name like `15_issue-13-14-15-8_shortened-title-hash/`.
    - Confirm the combined issue number (e.g., `13-14-15-8`) is preserved and visible in the directory name.
    - Check that subsequent phases (e.g., Spec after Analyst) reuse the exact same directory.
- [ ] **Determinism of Workspace Name**:
    - Run the same multi-issue Guided Planning task multiple times.
    - Verify that the generated planning workspace name is identical across all runs.
- [ ] **Short Title Compatibility**:
    - Run Guided Planning for a single issue or a few issues with a short combined title.
    - Verify that the generated workspace name is readable and not unnecessarily shortened.
- [ ] **Circular LLM Fallback (Recovery)**:
    - Configure LLM providers to simulate a transient failure for the initially active model.
    - Observe the planning workflow; it should attempt other configured models in a circular fashion.
    - Verify that planning successfully completes if an alternative model in the chain succeeds.
    - Check that the `active_llm_fallback_position` is updated to the index of the newly successful model.
    - Observe logs for clear indications of fallback attempts and successful model switches.
- [ ] **Circular LLM Fallback (Exhaustion)**:
    - Configure LLM providers to simulate failures for *all* models in the configured chain.
    - Initiate a Guided Planning run.
    - Verify that the system attempts each configured model once in a circular pass.
    - Confirm that the planning workflow ultimately reports a final failure only after exhausting the entire chain, without infinite loops.
    - Observe logs for clear indications that all recovery options were exhausted.

```