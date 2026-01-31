# Spec Kit Integration (SDD Workflow)

Transition Luma to **Spec-Driven Development (SDD)** by adopting concepts from [GitHub Spec Kit](https://github.com/github/spec-kit).

---

## Goal
Implement a native Spec-Driven workflow: **Specify (The What) -> Plan (The How) -> Code**.

## Core Components
*(Unchanged components section omitted for brevity)*

---

## Bug Fix: SpecKit Menu Access (Current Task)

### Goal Description
Fix a bug where menu option '3' has a conflict between "Refine Issue" (Legacy) and "Generate Spec" (New). The user wants to **keep both features**.

### Proposed Changes

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/Luma/main.py)
- **Update Menu Definitions**: Add "Refine Issue" to `MENU_ACTIONS` with key **'R'**.
- **Update Logic**:
    - Change the handler for `actions.action_refine_issue` from `choice == "3"` to `choice.upper() == "R"`.
    - Keep `choice == "3"` assigned to `actions.action_generate_spec`.

### Menu Mapping Plan
| Key | Action | Status |
| :--- | :--- | :--- |
| **3** | `action_generate_spec` (SpecKit) | ✅ Keep as is |
| **R** | `action_refine_issue` (Analyst) | 🆕 Reassign from '3' to 'R' |

## Verification Plan

### Manual Verification
1. Start Luma (`python main.py`)
2. Verify Menu UI shows **[R] Refine Issue**.
3. Select Issue involved in active task.
4. Run **[R]** -> Check if "Analyst Agent" runs.
5. Run **[3]** -> Check if "Spec Agent" runs.
