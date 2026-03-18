# Changelog

## [1.4.0] - 2026-03-19

### Added
- **[LLM Fallback]** Smart Fallback Strategy with Rate Limit detection and per-model timeout handling in `FallbackModel`.
- **[Error Classifier]** New `error_classifier.py` for identifying HTTP 429, Quota, and Timeout strings instantly.
- **[Usage Log]** Granular tracking of `error_type` in `usage_tracker.py` for LLM performance debugging.

### Changed
- **[Models]** Reordered `AVAILABLE_GEMINI_CLI_MODELS` to prioritize `gemini-2.5-flash` for overall speed/stability.
- **[Core]** `_add_new_project` ID generation modified to use auto-increment from existing project sequences instead of Unix epoch timestamp.

## [1.3.0] - 2026-01-31

### Added
- **[Spec Kit]** Adopted Spec-Driven Development (SDD) workflow.
- **[Docs]** Added `docs/constitution.md` (Project Rules) and templates for Spec (`spec.md`) and Plan (`plan.md`).
- **[Agents]** New `Spec Agent` (Menu: 3) and `Architect Agent` (Menu: P).
- **[Workflow]** New flow: Issue -> **Specify** -> **Plan** -> Code.

## [1.2.0] - 2026-01-31

### Added
- **[Draft Code Review]** New feature to generate `draft_code_review.md` with full git diff, commits, and stats.
- **[Menu]** Option "D" to manually trigger draft generation.
- **[Publisher]** Publisher Agent now auto-detects and uses `draft_code_review.md` for richer PR context.
- **[Tools]** `generate_draft_code_review()` function in `luma_core/tools.py`.

## [1.1.0] - 2026-01-31

### Added
- **[SBE]** Specification by Example (SBE) feature for pre-coding phase
- **[SBE Core]** `luma_core/sbe.py` with `Scenario`, `SBESpec` dataclasses
- **[SBE Agent]** AI-powered SBE generator (`luma_core/agents/sbe_agent.py`)
- **[SBE Template]** `docs/templates/sbe_template.md` for standardized format
- **[Menu]** New menu option "S" to generate SBE specs from active issue
- **[Tests]** 9 unit tests for SBE module

### Changed
- **[Actions]** Added `action_generate_sbe()` function
- **[Main]** Extended menu with SBE option

## [1.0.0] - 2026-01-30

### Added
- **[Luma V2]** Complete overhaul of the workflow engine ("Workflow Guardian")
- **[State Management]** Persistent state (`.luma_state.json`) to track phases: Idle, Selecting, Coding, Preflight, PR Pending
- **[UI V2]** New `ui.py` with responsive boxed interface, emoji support, and dynamic width calculation
- **[Actions V2]** Modular `actions.py` decoupling business logic from the main loop
- **[Config]** Centralized configuration in `luma_core/config.py` with explicit multi-repo support

### Changed
- **[Refactor]** `main.py` is now a lightweight controller (< 150 lines)
- **[UX]** Removed "Reset State" prompts; auto-save on project switch supported
- **[Docs]** Updated README to reflect V2 architecture

## [0.5.1] - 2026-01-29

### Added
- Initial release of the Luma AI Software Engineer agent.
- Core framework for autonomous task execution, including planning, implementation, and QA phases.
- Integration with GitHub for project management, issue tracking, and code manipulation.
- State management system to track agent progress and state.
- Introduced a rules-based system for guiding agent behavior.
- Comprehensive test suite for core components and agent flows.

## [0.5.0] - 2026-01-18

### Added
- **[Multi-Repo Docs]** AI-powered documentation generation for CHANGELOG.md and README.md
- **[Version Management]** Configurable version file per repository (VERSION, package.json, build.gradle)
- **[Git Diff Preview]** VS Code diff view for reviewing AI-generated documentation changes
- **[Version Detection]** Automatic version extraction from CHANGELOG entries

### Changed
- **[AI Prompts]** Improved README AI prompts to prevent hallucination and maintain content structure
- **[Config]** Added `version_file` configuration per project for precise version management

## [0.4.0] - 2026-01-18

### Added
- **[Multi-Repo PR]** Create Pull Requests across multiple JarWise repositories (Root, Android, Web)
- **[Multi-Repo Docs]** Update documentation across multiple repos with AI assistance
- **[Commit Check]** Verify unpushed commits before PR creation

## [0.3.0] - 2025-12-28

### Added
- **[Version Badges]** Automatically update README version badges
- **[AI Version Suggestion]** Semantic version bump suggestions based on commit types

## [0.2.0] - 2025-12-27

### Added
- **[LLM-Powered PR]** AI-generated Pull Request titles and descriptions
- **[Changelog Automation]** Auto-generate changelog entries from commits
- **[Documentation Review]** Automated documentation reviewer agent

## [0.1.0] - 2025-12

### Added
- **[Core]** Initial multi-agent system with Coder, Reviewer, Tester, and Publisher agents
- **[LangGraph]** Workflow orchestration using LangGraph
- **[GitHub Integration]** Issue-driven development mode
- **[Multi-LLM Support]** Google Gemini and OpenRouter support