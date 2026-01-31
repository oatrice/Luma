# Spec Kit Integration Walkthrough (v1.3.0)

## Summary
Luma now supports **Spec-Driven Development (SDD)** natively. This ensures that every feature starts with a clear Specification ("What") and a Technical Plan ("How") before coding begins.

## Key Changes

### 📂 New Files
- `docs/constitution.md`: The "Constitution" containing project rules.
- `docs/templates/spec_template.md`: Template for Specs (replacing Analysis).
- `docs/templates/plan_template.md`: Template for Implementation Plans.
- `luma_core/agents/spec_agent.py`: Agent to write Specs.
- `luma_core/agents/architect_agent.py`: Agent to write Plans.

### 🔄 Workflow Updates
- **Menu Option 3**: `🧬 Generate Spec (The What)`
- **Menu Option P**: `📐 Generate Plan (The How)`

---

## How to Use

1. **Start Issue**: Select an issue from Kanban (Option 2).
2. **Generate Spec**: Press `3`. Luma will create a `spec.md` in `docs/features/XX_feature_name/`.
   - *Review this file to ensure requirements are correct.*
3. **Generate Plan**: Press `P`. Luma will read the Spec and creating a `plan.md`.
   - *Review this file to approve the technical approach.*
4. **Implement**: Proceed to coding as usual (or handoff to Coder Agent in future).

---

## Example Structure
```
docs/features/1_issue-123_add-login/
├── spec.md  (The Requirement)
└── plan.md  (The Solution)
```
