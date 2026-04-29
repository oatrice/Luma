# Specification: Fix Invalid Selection When Adding Multiple Issues

> **Status**: Approved

> **Owner**: Kilo

> **Dates**: Created: 2026-04-29 | Last Updated: 2026-04-29

## 1. Context & Goal

*Why are we building this? What is the problem statement?*

### Problem

Users cannot efficiently add multiple issues to their current work session. When attempting to enter comma-separated issue numbers like "1,2,3", the system rejects the input as "Invalid selection", forcing users to add issues one at a time.

### Goal

Enable comma-separated input for adding multiple issues simultaneously, improving user efficiency and matching the behavior of issue selection.

---

## 2. User Journey & Requirements

*What should the user experience?*

### User Story

As a **developer working on multiple related issues**, I want to **add several issues at once using comma-separated input**, so that **I can quickly build my work session without repetitive individual selections**.

### Functional Requirements

- [x] Support comma-separated input (e.g., "1,2,3") for adding multiple issues

- [x] Maintain backward compatibility with single issue selection

- [x] Prevent duplicate issue additions

- [x] Provide clear error messages for invalid inputs

- [x] Update UI prompts to indicate multi-select capability

### Non-Functional Requirements

- [x] Performance: Input parsing should be fast (<100ms)

- [x] Reliability: Invalid inputs should not crash the system

- [x] Usability: Error messages should be clear and actionable

---

## 3. Specification by Example (SBE)

*Concrete examples of behavior.*

### Scenario: Add Multiple Issues Successfully

**Given** user is in CODING phase

**When** user chooses "Add Issue to Current Work Session"

**And** enters "1,2,3"

**Then** issues 1, 2, and 3 are added to active issues

**And** success messages are displayed

#### Examples

| Input Format | Issues Added | User Feedback |
|--------------|--------------|---------------|
| "1,2,3" | 3 issues | "✅ Added #61: Title1" etc. |
| "1" | 1 issue | "✅ Added #61: Title1" |
| " 1 , 2 " | 2 issues | Success messages |

### Scenario: Handle Invalid Inputs

**Given** user is prompted for issue selection

**When** user enters invalid input

**Then** system shows appropriate error messages

**And** no invalid issues are added

#### Examples

| Invalid Input | Error Response |
|---------------|----------------|
| "1,99" | "❌ Invalid index: 99" |
| "abc" | "❌ Invalid selection" |
| "0" | "❌ Invalid index: 0" |

---

## 4. Constraints & Risks

*What should we watch out for?*

- Constraint: Must maintain backward compatibility

- Risk: Parsing errors could cause unexpected behavior

- Risk: Performance impact from parsing multiple indices