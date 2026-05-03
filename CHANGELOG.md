# Changelog

## [0.25.0] - 2026-05-03

### Added
- **VCS_CLI Priority Logic**: Unified PR functions now respect VCS_CLI configuration with strict provider matching (glab+GitLab, gh+GitHub)
- **Self-Healing Fallback**: Automatic fallback to URL regex matching when VCS_CLI configuration doesn't match URL type, with configurable strict mode
- **Enhanced Error Handling**: Clear error messages for VCS_CLI mismatches with debug logging for CLI tool selection
- **Comprehensive Test Coverage**: Added 18 test cases covering VCS_CLI priority logic, error handling, and self-healing scenarios
- **Feature Documentation**: Complete analysis, specification, implementation plan, SBE, and manual verification guide for VCS CLI priority feature

### Changed
- **Platform Detector Functions**: Updated `check_pr_status_unified()`, `get_open_pr_unified()`, `update_pull_request_unified()`, and `create_pull_request_unified()` to use VCS_CLI priority logic
- **Refresh Workflow**: Enhanced PR status checking in refresh workflow to handle VCS migration scenarios with self-healing enabled by default
- **CLI Tool Selection**: VCS_CLI configuration now takes priority over URL regex matching for consistent tool selection
- **Debug Logging**: Added comprehensive logging for VCS CLI selection and self-healing decisions

### Fixed
- **Issue #93**: Resolved VCS_CLI configuration being ignored by unified PR functions, ensuring proper CLI tool selection based on user configuration

## [0.24.0] - 2026-05-01

### Added
- **GitLab Repository Support**: Full support for GitLab repositories including merge request creation and status checking
- **Platform Detection**: Automatic detection of GitHub vs GitLab repositories from URLs and git remotes
- **Unified PR Functions**: New unified functions for PR/MR creation, status checking, and updates across both platforms
- **VCS CLI Settings**: User-friendly interface to switch between GitHub CLI (`gh`) and GitLab CLI (`glab`) in settings
- **GraphQL Fallback**: Graceful handling of GraphQL operations for GitLab repositories where CLI doesn't support them
- **Comprehensive Documentation**: Complete feature documentation including analysis, spec, plan, SBE, and verification guide
- **Test Scripts**: Added test scripts for PR creation and status checking verification

### Changed
- **Repository Configuration**: Updated repository names from `oatrice/Luma` to `oatricedev/Luma` across all configuration files
- **Multi-Repo PR Creation**: Updated to use unified platform detection and appropriate CLI tools
- **Deploy Script**: Modified `scripts/deploy_pr.py` to use unified PR creation functions
- **Project Tools**: Updated `luma_core/tools.py` to use platform-aware PR functions
- **GitHub Project Integration**: Added graceful fallback for GitLab repositories in project operations
- **Main Application**: Enhanced PR status checking to work with both GitHub and GitLab repositories

### Fixed
- **PR Creation Errors**: Fixed "422 Validation Failed" errors when creating PRs on GitLab repositories
- **GraphQL Operations**: Fixed "GitLab CLI doesn't support GraphQL operations" errors with graceful fallbacks
- **Project Field Schema**: Fixed "Could not get project field schema" errors for GitLab repositories
- **PR URL Validation**: Fixed "Invalid PR URL" errors for GitLab merge request URLs
- **Platform Detection**: Improved detection logic for various repository URL formats (HTTPS, SSH, owner/repo)

## CHANGELOG.md Entry

## [0.23.0] - 2026-04-30

### Added
- **VCS CLI Support**: Implemented abstraction layer supporting both GitHub CLI (`gh`) and GitLab CLI (`glab`)
- **CLI Wrapper**: New [luma_core/cli_wrapper.py](cci:7://file:///Users/oatrice/Software-projects/Luma-worktrees/luma1/luma_core/cli_wrapper.py:0:0-0:0) module for unified VCS command execution
- **Configuration Options**: Added `VCS_CLI`, `GITLAB_TOKEN`, and `VCS_TOKEN` configuration variables
- **Command Conversion**: Automatic conversion between GitHub and GitLab CLI commands
- **GitLab Integration**: Full support for GitLab repositories with issue fetching and parsing
- **Comprehensive Testing**: Added 15 unit tests for CLI wrapper functionality
- **Documentation**: Complete feature documentation including analysis, spec, plan, SBE, and manual verification guide

### Changed
- **GitHub Client**: Refactored to use CLI wrapper instead of direct subprocess calls
- **Issue Metrics**: Updated to use configurable VCS CLI for GitHub/GitLab operations
- **Admin Actions**: Enhanced to support both GitHub and GitLab CLI tools
- **Project Integration**: Updated GitHub project sync to work with both CLI tools
- **Error Handling**: Improved error messages for VCS CLI compatibility
- **Token Management**: Enhanced token fallback chain supporting both GitHub and GitLab tokens

### Fixed
- **CLI Detection**: Improved detection and validation of VCS CLI tools
- **Output Parsing**: Added support for GitLab tab-separated output format
- **GraphQL Compatibility**: Graceful handling of GitLab CLI limitations with GraphQL operations

## [0.22.0] - 2026-04-29

### Added
- **CLI:** Multi-select support for adding and removing issues with comma-separated (e.g., "1,2,3") or space-separated (e.g., "1 2 3") input
- **Tests:** Comprehensive unit test coverage for multi-issue selection scenarios (10 tests total)
- **Documentation:** Feature spec, analysis, plan, SBE, and manual verification guide for Issue #90

### Changed
- **Issue Actions:** Enhanced `action_add_issue` and `action_remove_issue` to parse multi-select input with proper validation and error handling

## [0.21.0] - 2026-04-24

### Added
- **CLI:** Implemented stable prefixed project selectors for reliable headless project selection by repo, path, or slug
- **Documentation:** Added comprehensive design documents for stable CLI project selection feature
- **Tests:** Enhanced test coverage for headless bootstrap, selector docs, and main CLI functionality

### Fixed
- **Branch Validation:** Improved branch name validation for better consistency and error handling
- **Project Resolution:** Enhanced project selector stability to prevent cross-repo resolution conflicts

### Changed
- **Configuration:** Updated project configuration format to support stable prefixed selectors
- **Metrics:** Integrated issue data into Luma metrics tracking

## [0.20.0] - 2026-04-23

### Added
- **Documentation:** Added feature analysis, plan, spec, SBE, and a manual verification guide for the worktree resolution and canonical project identity fixes.

### Fixed
- **Code Review:** Preserved real target repository paths during headless multi-repo `code_review` runs from a Luma worktree.
- **Worktrees:** Limited worktree path remapping to repositories that belong to the same underlying git family as the active checkout.
- **Projects:** Resolved Luma worktree selections back to the canonical Luma project identity and GitHub Project board metadata.

### Removed
- **Documentation:** Removed redundant legacy feature documentation directories and duplicate AI Brain artifacts.

## [0.19.0] - 2026-04-10

### Added
- **Projects:** Introduced centralized project management via `.luma/projects.json` with full project configuration support.
- **UI/UX:** Enhanced Luma CLI header to display folder path, GitHub Project number, and worktree detection with `(worktree)` suffix.
- **AI Brain Sync:** Implemented project-aware filtering for AI brain sessions, showing only relevant sessions for the current project.
- **Menu:** Reorganized menu actions for improved accessibility - "Auto Full Workflow" (A) and "View Kanban Status" (K) now appear in top positions.
- **Documentation:** Added comprehensive feature documentation for Issues #74, #72, #71, #60 including spec, plan, analysis, and SBE.
- **Tests:** Added full test suite for header enhancement features and project-aware synchronization.

### Changed
- **Config:** Migrated project configuration from legacy format to new JSON-based project management system.
- **Version:** Standardized all version references to pre-release `0.x.x` format across VERSION file and CHANGELOG.
- **Admin Actions:** Enhanced AI brain synchronization to filter sessions by project context for cleaner output.

### Removed
- **Prompts:** Cleaned up obsolete prompt files from `.luma/prompts/` directory.


## [0.18.0] - 2026-04-10

### Added
- **LLM:** Restored auto-export of failed prompts with human-readable timestamps.

### Fixed
- **LLM:** Resolved feature directory path correctly with subdirectories.

## [0.17.0] - 2026-04-09

### เพิ่มเติม (Added)
- **LLM:** ใช้การปรับขนาด timeout, การลองใหม่ที่กำหนดเอง และการส่งออก prompt.
- **Metrics:** เพิ่มประเด็น #58 และ #59 ให้กับเมตริก.
- **Documentation:** เพิ่มเอกสารประกอบสำหรับประเด็น #58-59.

### แก้ไข (Fixed)
- **Worktree Paths:** แก้ไขปัญหาเส้นทาง worktree ใน LLM และ Workflow.

### ลบออก (Removed)
- **Documentation:** ลบเอกสารคุณสมบัติที่ซ้ำซ้อน.
- **Documentation:** ลบแผนการดำเนินการ, งาน, และ walkthrough สำหรับ AI brain ของประเด็น #53, #55-56.

## [0.16.0] - 2026-04-09

### Changed
- **Core:** Improved path resolution logic for Git worktrees, enhancing reliability when operating within multiple worktrees.

### Removed
- **Code Review:** Discontinued the automatic creation of temporary code review prompt text files.

## [0.15.0] - 2026-04-08

### Added
- **Worktree Orchestration:** Implemented a multi-agent worktree orchestration system, enabling Luma to manage and coordinate complex tasks across multiple Git worktrees simultaneously.
- **Git Detection:** Added automatic GitHub repository and Kanban board detection to improve project mapping and synchronization.
- **Documentation:** Introduced `WORKTREE_ORCHESTRATION_DESIGN.md` detailing the architectural design for multi-agent workflows.

### Changed
- **Core:** Enhanced planning and administrative actions to support worktree-aware operations.
- **Testing:** Added a comprehensive test suite for Git worktree detection and state validation.

## [0.14.0] - 2026-04-08

### Added
- **Headless CLI:** Expanded the headless contract to support guided workflows, issue selection (mirroring interactive menus), and programmatic issue bootstrapping.
- **GitHub Projects:** Implemented automatic addition of new issues to GitHub Projects, including Kanban mapping integration for the Zenith repository.
- **Workflow:** Enabled forced Pull Request creation across all development phases.
- **Documentation:** Added a manual verification guide for headless synchronization.

### Changed
- **Core:** Enhanced project key resolution using path detection logic for more accurate project mapping.
- **Stability:** Improved dynamic project support and overall stability of headless execution paths.

### Fixed
- **Output:** Standardized `IssueData` fields and suppressed unnecessary stdout to prevent JSON pollution in headless mode.
- **Branch Management:** Added validation and auto-repair mechanisms for invalid branch states.

## [0.13.0] - 2026-04-03

### Added
- **Dotfiles Bootstrap:** Implemented a portable dotfiles bootstrap template, including AI dotfiles, to facilitate the management of shared AI memory configurations.
- **Release Versioning:** Enforced unique and sequential release versions for improved release management.

### Changed
- Updated core tools and package configurations.
- Refined metrics tracking and agent configurations.

## [0.12.0] - 2026-04-03

### Added
- **Guided Planning:** Enhanced multi-issue planning with compact naming, safe directory generation, and improved circular LLM fallback.
- **Usage Tracking:** Implemented recording of action events and filtering for metric logs.
- **Feature Directories:** Centralized logic for feature directory naming.
- **Metrics:** Added functionality to prompt for post story points, enhancing effort tracking.

### Fixed
- **LLM:** Resolved an issue with the fallback model rotation logic.

## [0.11.0] - 2026-04-03

### Added
- **CLI:** Introduced action-level logging for headless CLI executions to improve debuggability.
- **Metrics:** Added a prompt to record post-story points for actual effort tracking against initial estimates.

## [0.10.0] - 2026-04-02

### Added
- **CLI:** Introduced a headless metadata endpoint for programmatic interaction and ensured strict JSON output for external callers.

## [0.9.0] - 2026-04-02

### Added
- **CLI:** Introduced a headless CLI contract for programmatic execution, allowing external callers to interact with Luma programmatically. Updated documentation to include analysis for this new feature.

## [0.8.0] - 2026-04-01

### Added
- **LLM Providers:**
    - Expanded LLM provider support with the addition of Codex CLI.
    - Enhanced Gemini CLI model error handling and logging.
    - Improved LLM fallback by resetting the fallback index when the LLM provider changes.
- **Usage Tracking:**
    - Introduced tracking for branch suggestion action context.

### Fixed
- **Kanban Sync:**
    - Prevented Kanban synchronization issues caused by missing IDs.

## [0.7.0] - 2026-03-31

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

## [0.6.0] - 2026-03-30

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

## [0.5.2] - 2026-03-25

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

## [0.4.1] - 2026-03-19

### Fixed
- **[Config]** Resolved an issue where nested dictionary configurations were being overwritten instead of deep-merged, preventing potential data loss in project-specific settings.

## [0.4.0] - 2026-03-19

### Added
- **[LLM Fallback]** Smart Fallback Strategy with Rate Limit detection and per-model timeout handling in `FallbackModel`.
- **[Error Classifier]** New `error_classifier.py` for identifying HTTP 429, Quota, and Timeout strings instantly.
- **[Usage Log]** Granular tracking of `error_type` in `usage_tracker.py` for LLM performance debugging.

### Changed
- **[Models]** Reordered `AVAILABLE_GEMINI_CLI_MODELS` to prioritize `gemini-2.5-flash` for overall speed/stability.
- **[Core]** `_add_new_project` ID generation modified to use auto-increment from existing project sequences instead of Unix epoch timestamp.

## [0.3.1] - 2026-01-31

### Added
- **[Spec Kit]** Adopted Spec-Driven Development (SDD) workflow.
- **[Docs]** Added `docs/constitution.md` (Project Rules) and templates for Spec (`spec.md`) and Plan (`plan.md`).
- **[Agents]** New `Spec Agent` (Menu: 3) and `Architect Agent` (Menu: P).
- **[Workflow]** New flow: Issue -> **Specify** -> **Plan** -> Code.

## [0.3.0] - 2026-01-31

### Added
- **[Draft Code Review]** New feature to generate `draft_code_review.md` with full git diff, commits, and stats.
- **[Menu]** Option "D" to manually trigger draft generation.
- **[Publisher]** Publisher Agent now auto-detects and uses `draft_code_review.md` for richer PR context.
- **[Tools]** `generate_draft_code_review()` function in `luma_core/tools.py`.

## [0.2.0] - 2026-01-31

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

## [0.1.0] - 2026-01-30

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

## [0.3.2] - 2026-01-18

### Added
- **[Multi-Repo PR]** Create Pull Requests across multiple JarWise repositories (Root, Android, Web)
- **[Multi-Repo Docs]** Update documentation across multiple repos with AI assistance
- **[Commit Check]** Verify unpushed commits before PR creation

## [0.2.2] - 2025-12-28

### Added
- **[Version Badges]** Automatically update README version badges
- **[AI Version Suggestion]** Semantic version bump suggestions based on commit types

## [0.1.1] - 2025-12-27

### Added
- **[LLM-Powered PR]** AI-generated Pull Request titles and descriptions
- **[Changelog Automation]** Auto-generate changelog entries from commits
- **[Documentation Review]** Automated documentation reviewer agent

## [0.0.1] - 2025-12

### Added
- **[Core]** Initial multi-agent system with Coder, Reviewer, Tester, and Publisher agents
- **[LangGraph]** Workflow orchestration using LangGraph
- **[GitHub Integration]** Issue-driven development mode
- **[Multi-LLM Support]** Google Gemini and OpenRouter support
