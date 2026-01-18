# Changelog

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
