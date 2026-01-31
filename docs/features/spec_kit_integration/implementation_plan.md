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

## Verification Plan

### Automated Checks
- Run import check script to verify new modules load correctly.
- (Done: `✅ Spec Kit Integrations OK`)

### Manual Verification
1. Start Luma (`python main.py`)
2. Select Issue.
3. Run **[3] Generate Spec** -> Verify `docs/features/X/spec.md` created.
4. Run **[P] Generate Plan** -> Verify `docs/features/X/plan.md` created.
