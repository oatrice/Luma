# SBE (Specification by Example) Template

> 📅 Created: 2026-03-19
> 🔗 Issue: https://github.com/oatrice/Luma/issues/9

---

## Feature: Tracking Estimate Points, Mandays, and Effort

This feature enables the team to track and manage development performance, velocity, and resource planning by adding support for structured input of Estimate Points, Mandays, and Effort for issues and tasks across all projects. It provides a data structure suitable for exporting and analyzing performance metrics.

### Scenario: Successfully Input and Edit Metrics - Happy Path

**Given** an existing issue in any project and the user has permissions to edit it
**When** the user provides valid Estimate Points, Mandays, and Effort values for the issue
**Then** the new metrics are saved, associated with the issue, and persist across sessions

#### Examples

| Issue ID | Estimate Points | Mandays | Effort Level | Saved Estimate Points | Saved Mandays | Saved Effort Level |
|----------|-----------------|---------|--------------|-----------------------|---------------|--------------------|
| Luma-101 | 8               | 5       | High         | 8                     | 5             | High               |
| Luma-102 | 3               | 2       | Medium       | 3                     | 2             | Medium             |
| Luma-103 | 13              | 10      | High         | 13                    | 10            | High               |
| Luma-104 | 5               | 3       | Low          | 5                     | 3             | Low                |
| Luma-105 | 2               | 1       | Medium       | 2                     | 1             | Medium             |

---

### Scenario: Handling Invalid Metric Inputs - Error Handling

**Given** an existing issue and the user attempts to input metrics
**When** the user provides invalid (non-numeric, negative, or unrecognized string for effort) values for Estimate Points, Mandays, or Effort
**Then** the system rejects the input and displays a clear error message without saving the invalid data

#### Examples

| Issue ID | Estimate Points | Mandays | Effort Level | Expected Error Message                                  |
|----------|-----------------|---------|--------------|---------------------------------------------------------|
| Luma-106 | -5              | 3       | High         | Estimate Points must be a positive integer.             |
| Luma-107 | 8               | "abc"   | Medium       | Mandays must be a numeric value.                        |
| Luma-108 | 5               | 2       | "Very High"  | Effort Level must be 'Low', 'Medium', or 'High'.        |
| Luma-109 | 0               | 1       | Low          | Estimate Points must be a positive integer greater than 0. |
| Luma-110 | 1               | -2      | Medium       | Mandays must be a positive number.                      |

---

### Scenario: Aggregating Metrics Across Projects - Boundary Conditions

**Given** multiple issues across different projects have valid Estimate Points, Mandays, and Effort recorded
**When** the system is prompted to collect and aggregate these metrics across different projects
**Then** the aggregated metrics (e.g., total points, total mandays, average effort) are correctly calculated and a performance summary is generated

#### Examples

| Project  | Issue ID | Estimate Points | Mandays | Effort Level |
|----------|----------|-----------------|---------|--------------|
| Project A| A-001    | 5               | 3       | High         |
| Project A| A-002    | 3               | 2       | Medium       |
| Project B| B-001    | 8               | 5       | High         |
| Project B| B-002    | 2               | 1       | Low          |
| Project C| C-001    | 13              | 10      | High         |

---

## Notes

- Effort Level is expected to be a categorical input, e.g., 'Low', 'Medium', 'High'.
- Mandays can be a decimal value (e.g., 0.5 for half a day).
- Estimate Points are expected to be positive integers.
- The system should define clear boundaries for "positive" (e.g., > 0) for numerical inputs.
- Aggregation should consider issues that might not have all three metrics filled, potentially defaulting missing values to zero for calculation purposes or excluding them as per configuration.
- The mechanism to collect and aggregate metrics should be accessible via a command or UI, and provide options for filtering by project, date range, etc.