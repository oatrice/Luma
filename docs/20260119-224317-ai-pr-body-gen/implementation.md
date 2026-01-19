# Implementation Plan: AI-Enhanced PR Description

## Goal
Enhance the `publisher_agent` in `luma_core` to automatically generate descriptive and context-aware Pull Request bodies using an LLM. This will replace the current static generation method.

## User Review Required
- **LLM Cost**: This will introduce an additional LLM call per PR creation.
- **Latency**: Generating the PR description will add a few seconds to the process.

## Proposed Changes

### Component: `luma_core/agents/publisher.py`

#### [MODIFY] publisher.py
- **Logic**:
    1.  **Retrieve Context**: After the git commit step, capture the diff or commit summary (e.g., using `git show --stat --oneline HEAD`).
    2.  **Load Template**: Continue to load `.github/pull_request_template.md` if it exists.
    3.  **Construct Prompt**: Create a prompt for the LLM that includes:
        - The Task/Issue Title.
        - The Issue Description (if available).
        - The Commit Summary/Diff stats.
        - The PR Template text (with instructions to fill it out or follow its structure).
    4.  **Save Draft Prompt**: Write the constructed prompt to a file (e.g., `draft_pr_prompt.txt`) for debugging/audit.
    5.  **Manual Approval**: Print the path of the draft prompt and pause execution using `input()`, asking the user to review and verify before proceeding.
    6.  **Generate**: Call `get_llm()` to generate the PR body response.
    7.  **Fallback**: Ensure there's a fallback to the simple task description if the LLM call fails.

## Verification Plan

### Manual Verification
1.  Run `main.py`.
2.  Select **Option 2** (Create Pull Request).
3.  Observe the console output for "🤖 Generating PR Body with AI...".
4.  Check the created Pull Request on GitHub to verify the body is detailed and follows the template (if applicable).
