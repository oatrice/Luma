# SBE (Specification by Example) Template

> 📅 Created: [DATE]
> 🔗 Issue: [ISSUE_URL]

---

## Feature: [FEATURE_NAME]

[FEATURE_DESCRIPTION]

### Scenario: [SCENARIO_NAME_1] - Happy Path

**Given** [PRECONDITION]
**When** [ACTION]
**Then** [EXPECTED_OUTCOME]

#### Examples

| [INPUT_VAR_1] | [INPUT_VAR_2] | [EXPECTED_VAR] |
|---------------|---------------|----------------|
| [value]       | [value]       | [value]        |
| [value]       | [value]       | [value]        |
| [value]       | [value]       | [value]        |

---

### Scenario: [SCENARIO_NAME_2] - Edge Case / Error Handling

**Given** [PRECONDITION]
**When** [INVALID_ACTION]
**Then** [ERROR_HANDLING_OUTCOME]

#### Examples

| [INPUT_VAR] | [EXPECTED_ERROR] |
|-------------|------------------|
| empty       | [error message]  |
| null        | [error message]  |
| overflow    | [error message]  |

---

### Scenario: [SCENARIO_NAME_3] - Boundary Conditions (Optional)

**Given** [PRECONDITION]
**When** [BOUNDARY_ACTION]
**Then** [BOUNDARY_OUTCOME]

#### Examples

| [BOUNDARY_INPUT] | [EXPECTED] |
|------------------|------------|
| min_value        | [result]   |
| max_value        | [result]   |
| zero             | [result]   |

---

## Notes

- [Any additional notes or assumptions]
