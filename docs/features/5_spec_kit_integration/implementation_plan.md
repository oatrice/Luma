# Spec Kit Integration (SDD Workflow)

Transition Luma to **Spec-Driven Development (SDD)** by adopting concepts from [GitHub Spec Kit](https://github.com/github/spec-kit).

---

## Goal
Implement a native Spec-Driven workflow: **Specify (The What) -> Plan (The How) -> Code**.

## Core Components

### 1. Constitution (`docs/constitution.md`)
- Defines standard rules and principles for all AI agents.
- Injected into prompts to ensure consistency.

### 2. Templates (`docs/templates/`)
- **`spec_template.md`**: Focuses on User Requirements, Context, and SBE Scenarios.
- **`plan_template.md`**: Focuses on Technical Implementation steps and Architecture.

### 3. New Agents (`luma_core/agents/`)
- **`spec_agent.py`**: Generates `spec.md` from Issue + Constitution.
- **`architect_agent.py`**: Generates `plan.md` from `spec.md` + Constitution.

### 4. Workflow Integration (`main.py`)
- **Menu [3]**: Generate Spec (`action_generate_spec`)
- **Menu [P]**: Generate Plan (`action_generate_plan`)

---

## Bug Fix: SpecKit Menu Access (Current Task)

### Goal Description
Fix a bug where menu option '3' ("Generate Spec") is incorrectly routed to "Refine Issue" due to duplicate logic in `main.py`.

### Proposed Changes

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/Luma/main.py)
- Remove the stale `elif choice == "3":` block (approx line 148) that calls `actions.action_refine_issue`.
- Ensure the correct `elif choice == "3":` block (approx line 208) that calls `actions.action_generate_spec` is active and correctly placed.

---

## Verification Plan

### Automated Checks
- Run import check script to verify new modules load correctly.
- (Done: `✅ Spec Kit Integrations OK`)

### Manual Verification
1. Start Luma (`python main.py`)
2. Select Issue.
3. Run **[3] Generate Spec** -> Verify PROMPT asks for SBE/Spec generation (not Refine Issue).
