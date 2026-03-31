# Implementation Plan - Auto Workflow Resumption Optimization

## Goal
Optimize the Luma CLI "Auto Full Workflow" by implementing skipping logic for completed steps.

## Proposed Changes
### `luma_core/actions/workflow_actions.py`
- Modify `action_guided_workflow` to check `state.checklist` and `state.phase` before each major step.
- Skip Planning (Step 2) and Coding (Step 3) if already completed.

### `tests/test_action_guided_workflow_resume.py` [NEW]
- Add a test that sets up a state in the `REVIEWING` phase with planning and coding already marked as complete.
- Verify that only the relevant subsequent steps (Review, Docs, Roadmap, etc.) are called.

## Verification
- Run `pytest tests/test_action_guided_workflow_resume.py` and ensure it passes.
