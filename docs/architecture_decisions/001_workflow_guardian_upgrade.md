# ADR 001: Luma Workflow Guardian Upgrade

## Status
Accepted

## Context
Luma was originally a static menu CLI. To better manage AI-assisted development workflows, it needed to evolve into a state-based workflow orchestrator capable of tracking real-time project state, synchronizing with GitHub Projects (Kanban), enforcing Pre-flight checks before PR creation, and summarizing context for new tasks.

## Decision
We decided to upgrade the Luma architecture to the "Workflow Guardian" model.
Key architectural components introduced:
1. **State Manager (`luma_core/state_manager.py`)**: Manages the project state (`.luma_state.json`) including phases (idle, selecting, coding, preflight, pr_pending) and checklist progress.
2. **Workflow Orchestrator**: Replaces the static menu with a state-aware dashboard.
3. **Pre-flight Checker (`luma_core/preflight_checker.py`)**: Enforces Definition of Done using rules configured in a project-specific `.luma_rules.json` file.
4. **Context Summarizer (`luma_core/context_summarizer.py`)**: Parses markdown rules and summarizes them for the agent.
5. **VCS/Project Integration**: Abstracts the project management layer to fetch and sync kanban cards using the configured CLI tool (`gh` for GitHub or `glab` for GitLab), enabling cross-platform workflow orchestration.

## Consequences
- **Positive**: Agents and developers have a unified state of truth. Pre-flight checks prevent incomplete PRs. Context summarization reduces token usage and improves AI focus.
- **Negative/Constraints**: Requires users to have the relevant VCS CLI (`gh` or `glab`) installed and authenticated. Introduces new config file (`.luma_rules.json`) that must be maintained per project.
