# Implementation Plan: Global Input Stabilization (The Final Sweep)

We will perform a comprehensive, project-wide replacement of all standard `input()` calls with `ui.safe_input()` to eliminate the `^M` terminal hang issue once and for all.

## User Review Required

> [!IMPORTANT]
> This is a high-volume refactor affecting over 10 files and 40+ lines of code. It is necessary because any remaining `input()` call in the entire workflow chain can trigger the terminal buffering bug.

## Proposed Changes

### Core UI Logic

#### [MODIFY] [ui.py](file:///Users/oatrice/Software-projects/Luma/luma_core/ui.py)
- Ensure `safe_input` is robust and all internal references to `input()` are removed or commented out.

### Action Modules (The "Hot" Zone)

#### [MODIFY] [workflow_actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions/workflow_actions.py)
- Replace all ~20 remaining `input()` calls with `ui.safe_input()`.

#### [MODIFY] [utils.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions/utils.py)
- Replace all `input()` calls with `ui.safe_input()`.

#### [MODIFY] [quality_actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions/quality_actions.py)
- Replace all `input()` calls with `ui.safe_input()`.

### Intelligence Layer

#### [MODIFY] [publisher.py](file:///Users/oatrice/Software-projects/Luma/luma_core/agents/publisher.py)
- Import `safe_input` from `luma_core.ui`.
- Replace all `input()` calls.

### General Tools

#### [MODIFY] [tools.py](file:///Users/oatrice/Software-projects/Luma/luma_core/tools.py)
- Import `safe_input` from `luma_core.ui`.
- Replace all `input()` calls.

## Open Questions
- Are there any specific prompts where a standard `input()` is preferred (e.g. for long text entry)? 
  - *Recommendation*: Use `safe_input` everywhere for consistency, as it handles single-line entries much more reliably in this environment.

## Verification Plan

### Automated Tests
- Run `python3 -m pytest ../Luma/tests/test_safe_input.py` to ensure core utility remains healthy.
- Run `grep -r "input(" luma_core/` after execution to confirm ZERO remaining calls.

### Manual Verification
- Restart Luma CLI and navigate through the "Skip Planning Phase" prompt to confirm `0` works without `^M`.
