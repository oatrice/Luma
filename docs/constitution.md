# Constitution

This document defines the core principles, rules, and non-negotiable standards for this project. All AI agents and developers must adhere to these guidelines.

## 1. Prime Directives
- **User First**: Always prioritize user experience and value.
- **Spec-Driven**: No code without a Spec. The Spec (`spec.md`) is the source of truth.
- **Plan Before Build**: No implementation without a Technical Plan (`plan.md`).
- **Simplicity**: Prefer simple, readable code over clever, complex solutions.

## 2. Technology Stack & Constraints

### General
- **Language**: Python 3.9+ (Backend/CLI), TypeScript (Frontend).
- **Documentation**: Markdown for all docs.

### Luma Core (Specific)
- **Modular**: Keep business logic in `luma_core/actions.py`, UI in `ui.py`.
- **State**: Ensure `LumaState` consistency.
- **Tools**: Use `luma_core/tools.py` for reusable utilities.

## 3. Coding Standards
- **Naming**: `snake_case` for Python, `camelCase` for JS/TS.
- **Type Hints**: Mandatory for all Python functions.
- **Comments**: Explain *why*, not just *what*.
- **Tests**: TDD is encouraged. All features must have unit tests.

## 4. Workflow Rules
1. **Specify**: Define the "What" and "Why" in `spec.md`.
2. **Plan**: Define the "How" in `plan.md`.
3. **Review**: User must approve Spec and Plan.
4. **Implement**: Code based on Plan.
5. **Verify**: Run tests and manual checks.

## 5. Security & Safety
- **Secrets**: Never hardcode API keys or secrets. Use `.env`.
- **Validation**: Validate all inputs from external sources (User, API, Git).
