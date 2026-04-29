# SBE (Specification by Example) Template

> 📅 Created: 2026-04-29

> 🔗 Issue: https://github.com/oatrice/Luma/issues/90

---

## Feature: Support Comma-Separated Multiple Issue Selection in Add Issue

The system should allow users to add multiple issues to the current work session by entering comma-separated issue numbers (e.g., "1,2,3").

### Scenario: Successful Addition of Multiple Issues

**Given** the user is in the CODING phase with an active issue

**When** the user selects "Add Issue to Current Work Session"

**And** enters "1,2,3" when prompted for issue selection

**Then** issues 1, 2, and 3 are added to the active issues list

**And** a success message is displayed for each added issue

#### Examples

| Input | Expected Issues Added | Success Message |
|-------|-----------------------|-----------------|
| "1,2,3" | Issues 1, 2, 3 | "✅ Added #61: Title1", "✅ Added #62: Title2", "✅ Added #63: Title3" |
| "1" | Issue 1 | "✅ Added #61: Title1" |
| "2,4" | Issues 2, 4 | "✅ Added #62: Title2", "✅ Added #64: Title4" |

---

### Scenario: Invalid Index Handling

**Given** the user is prompted to select issues

**When** the user enters an invalid index like "1,99"

**Then** valid issues are added and invalid indices are reported

**And** an error message is shown for invalid indices

#### Examples

| Input | Valid Issues Added | Error Message |
|-------|-------------------|---------------|
| "1,99" | Issue 1 | "❌ Invalid index: 99" |
| "0,1" | None | "❌ Invalid index: 0" |
| "abc,1" | Issue 1 | "❌ Invalid selection" |

---

### Scenario: Duplicate Issue Prevention

**Given** issue 1 is already active

**When** the user enters "1,2"

**Then** issue 1 is skipped with a warning

**And** issue 2 is added successfully

#### Examples

| Input | Already Active | Added | Skipped | Messages |
|-------|----------------|-------|---------|----------|
| "1,2" | Issue 1 | Issue 2 | Issue 1 | "⚠️ #61 already active, skipping", "✅ Added #62: Title2" |
| "3,3" | None | Issue 3 | None | "✅ Added #63: Title3" |

---

## Notes

- Indices are 1-based corresponding to the displayed list

- Single issue selection continues to work as before

- Comma-separated parsing handles whitespace around commas