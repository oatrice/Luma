# Changelog

## [1.7.0] - 2026-03-31

### Added
- **Metrics & Estimation:**
    - Introduced `post_story_point` tracking in `.luma_metrics.json` and `IssueMetricsRecord` to record actual effort vs. initial estimates.
    - Added comprehensive feature analysis and technical specifications for post-implementation metrics.
- **CLI Experience:**
    - Enhanced state refresh feedback with change detection, providing clear visibility when the workspace state is updated.

### Fixed
- **Stability:**
    - Added a timeout to subprocess calls within the issue activity hint logic to prevent potential CLI hangs during Git operations.

### Changed
- **Workflow Automation:**
    - Refined workflow planning logic with improved skip detection and more robust Pull Request identification.
    - Updated the metrics summarizer and report generator to integrate and display post-implementation story point data.

## [1.6.0] - 2026-03-30

### Added
- **LLM & Credential Rotation System:**
    - Implemented a robust `CredentialManager` supporting Google Account and API Key rotation.
    - Added **Global Cooldown Synchronization** and automatic failover (switching keys immediately upon 429 Rate Limits).
    - Support for named singletons in credential management.
    - Automatic masking of sensitive account info in logs for enhanced security.
- **Workflow & Metrics:**
    - Added a **Reviewing Phase** to menu actions and enabled Pull Request (PR) creation directly from this phase.
    - Introduced branch-based filtering and sub-action timing to the metrics dashboard.
- **Project Roadmap:**
    - Added version and note preservation during status updates.

### Fixed
- **LLM Engine & API:**
    - Fixed `TypeError: 'tuple' object has no attribute 'content'` in `GeminiAPIModel` by standardizing `invoke()` usage and `ChatResult` wrapping.
    - Prevented duplicate `run_manager` instances in `kwargs`.
    - Unified response handling across CLI and API models.
- **Stability & CLI:**
    - Hardened credential rotation logic and fixed interactive test failures.
    - Resolved Gemini CLI OAuth profile isolation issues via `HOME` environment override.

### Changed
- **UI & Input Handling:**
    - Standardized the use of `safe_input` for all user prompts.
    - Implemented the Input Stabilization plan and documentation.
- **Documentation:**
    - Established project-wide conventions with the introduction of `AGENTS.md`.
    - Synchronized AI brain artifacts and updated internal documentation.
- **Refactors:**
    - Standardized Gemini provider naming conventions.
    - Improved GitHub metrics synchronization for reopened issues and paradoxes.

## [1.5.0] - 2026-03-25

### Added
- **[Metrics & Reporting]** Introduced comprehensive project and issue tracking.
  - Added feature tracking with estimates for points, man-days, and effort levels.
  - Implemented automatic project report generation, including summaries of completed issues with creation, due, and completion dates.
  - Reports are now synchronized with the project roadmap and sorted by completion date.
  - Added a usage and metrics dashboard for better project visibility.
- **[Workflow]** Enhanced multi-repository and agent capabilities.
  - CI checks now run in the background for improved performance.
  - LLM agents now load project context for more accurate cross-repository planning.
  - Added interactive project selection for multi-repo documentation updates.
  - Implemented auto-filling of issue metrics from the roadmap.
- **[Notifications]** Added a test action to the CLI for Telegram notifications.

### Changed
- **[Planning]** Simplified planning agent execution and prioritized repository selection during the planning phase.
- **[Notifications]** Notification source now includes the current directory for better context.

### Fixed
- **[Reporting]** Corrected a datetime parsing error by handling the UTC timezone suffix ('Z').
- **[Reporting]** Ensured unique filenames are generated for project reports to prevent overwrites.
- **[Workflow]** Resolved an `UnboundLocalError` in a guided workflow test.

## [1.4.1] - 2026-03-19

### Fixed
- **[Config]** Resolved an issue where nested dictionary configurations were being overwritten instead of deep-merged, preventing potential data loss in project-specific settings.

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