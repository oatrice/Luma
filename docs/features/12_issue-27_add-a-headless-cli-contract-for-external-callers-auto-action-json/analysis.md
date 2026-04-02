# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Add a headless CLI contract for external callers (--auto, --action, --json) |
| **Date** | 2 เมษายน 2026 |
| **Analyst** | นักวิเคราะห์เทคนิคอาวุโส |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
The Luma CLI (`main.py`) currently lacks support for headless execution arguments (`--auto`, `--action`, `--json`), which are expected by external callers like `Zenith`. This prevents reliable programmatic invocation of Luma's functionalities for automation, code review, and planning workflows. Manual verification shows that `main.py` only recognizes the `--project` flag, rejecting others.
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | An external integration (e.g., `Zenith`) | programmatically invoke Luma CLI actions with specific arguments (`--auto`, `--action`, `--json`, `--project`) | I can automate workflows such as code review and project planning. |
| 2 | A developer integrating with Luma CLI | receive machine-readable output (JSON) and consistent non-zero exit codes for programmatic calls | I can reliably parse results and handle errors in automated scripts. |

### 1.3 Acceptance Criteria

- [ ] **AC1:** The command `python3 main.py --auto --action code_review --json --project 1` is accepted by the CLI without unrecognized argument errors.
- [ ] **AC2:** In case of successful execution, the CLI returns valid JSON on stdout, adhering to the defined success schema.
- [ ] **AC3:** In case of failure (e.g., invalid arguments, execution error), the CLI returns valid JSON error message on stderr and exits with a non-zero status code.
- [ ] **AC4:** The headless CLI contract (supported flags, JSON schema, exit codes) is documented for external integrations.

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[CLI Command Execution: `python3 main.py --auto --action <action_name> --json --project <id>`] --> B{Argument Parsing};
    B -- Valid Args --> C[Map `--action` to internal handler];
    B -- Invalid Args --> D[Output Error Message (stderr)];
    C --> E[Execute Action Logic];
    E --> F[Generate JSON Output (stdout)];
    F --> G[Set Exit Code (0 for success)];
    D --> H[Set Exit Code (non-zero for failure)];
    G --> I[Completion];
    H --> I;
```

### 2.2 Screen/Page Requirements

> [!IMPORTANT]
> **Policy**: N/A for CLI-based features.

| หน้าจอ | Actions | Components | UI Mock Status |
|--------|---------|------------|----------------|
| N/A | N/A | N/A | ✅ Done |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `--auto` | boolean | ✅ (for headless) | N/A |
| `--action <name>` | string | ✅ (for headless) | Must map to a valid internal action (e.g., `code_review`, `plan`, etc.) |
| `--json` | boolean | ✅ (for headless) | N/A |
| `--project <key>` | string | ✅ (for headless) | Must be a valid project identifier recognized by Luma. |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `stdout` | string | JSON string representing the outcome. |
| `stderr` | string | Error messages (for invalid arguments or execution failures). |
| `exit_code` | integer | 0 for success, non-zero for failure. |

**JSON Structure (Success):**
```json
{"status":"success","action":"<action_name>","project":"<project_id>","result":{...}}
```
*(The `result` object will contain action-specific data.)*

**JSON Structure (Failure):**
```json
{"status":"error","action":"<action_name>","error":"<error_message>","project":"<project_id>"}
```
*(Fields like `action` and `project` may be omitted if parsing failed early.)*

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `main.py` | 🔴 High | Primary entry point; requires modifications to `argparse` for new flags, logic to dispatch actions based on `--action`, and implementation of JSON output/exit codes. |
| `luma_core/actions/` | 🟡 Medium | Individual action functions may need to be refactored to be callable directly with parameters and return structured data instead of relying on interactive prompts. |
| `luma_core/ui.py` | 🟡 Medium | Needs to ensure that interactive UI elements are suppressed when `--auto` is present and that CLI argument parsing does not conflict with interactive mode. |
| Documentation (`README.md`, etc.) | 🔴 High | New documentation must be created or existing documentation updated to describe the headless CLI contract. |
| `luma_core/state_manager.py` | 🟢 Low | Indirectly affected if actions invoked via CLI modify state. |

### 3.2 Breaking Changes

- [ ] **BC1:** Existing interactive CLI usage might be affected if argument parsing changes are not carefully managed. The introduction of `--auto` should isolate headless mode, but thorough testing is required.
- [ ] **BC2:** External scripts or workflows relying on the *current* output format or error handling of `main.py` (if any were attempted) will break. This feature aims to establish a *new*, stable contract for automation.

### 3.3 Backward Compatibility Plan

```
Ensure that the default, interactive mode of `main.py` remains functional and unaffected when the new headless flags (`--auto`, `--action`, `--json`) are not used. The `--project` flag should continue to be supported for both interactive and headless modes.
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

> [!IMPORTANT]
> **Android Build Policy**: N/A for this Python CLI feature.

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python's `argparse` module natively supports adding new flags, defining required arguments, and handling different data types. Standard libraries for JSON handling (`json`) and exit codes (`sys.exit`) are available. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | The development team has expertise in Python, CLI development, and handling JSON data. No new technologies are required. |
| Infrastructure รองรับหรือไม่? | ✅ | No changes to existing infrastructure are anticipated. The CLI runs on the user's system. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 2-3 days (for one developer) |
| **Deadline** | Not specified in issue. |
| **Buffer Time** | Standard buffer to be applied. |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Development Time | Standard | Covered by existing team resources. |
| **Total** | N/A | No direct budget impact. |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| Project Identifiers (`--project`) | 🟢 Normal | Passed as arguments; actions invoking these must handle access control. |
| LLM API Keys / GitHub Credentials | 🔴 Critical | Handled by `credential_manager.py` and environment variables (`.env`). CLI itself does not expose or directly manage these. Actions must use them securely. |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Command Injection | 🔴 High | Use Python's `argparse` for parsing and validate all inputs rigorously. Avoid constructing shell commands with user-provided arguments directly. |
| Denial of Service | 🟡 Medium | Implement robust error handling for argument parsing and action execution. Ensure JSON output is well-formed. |
| Sensitive Data Exposure | 🟡 Medium | Ensure invoked actions do not log or print sensitive information. The CLI wrapper itself should not handle secrets directly. |

### 5.3 Authentication & Authorization

```
Authentication (e.g., GitHub tokens) and authorization for project access will be handled by the underlying Luma core components and actions, leveraging existing mechanisms like `gh CLI` or configured credentials. The `--project` flag will be passed to these components. The CLI contract itself does not introduce new authentication flows but enables existing ones.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| CLI Argument Parsing & Dispatch | < 50ms | N/A (will be measured post-implementation) |
| Action Execution Time | N/A (depends on action) | N/A |
| Exit Code Consistency | 100% | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Single User CLI Invocation | N/A | N/A (CLI is process-based) |
| Concurrent Scripted Calls | N/A | Scalability depends on the Luma backend and actions; this feature does not impede or directly enhance it. |
| Growth (1yr) | N/A | N/A |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Headless CLI Capability | Limited/Unsupported | Robust support for `--auto`, `--action`, `--json`, and consistent outputs. | High: Feature directly addresses this gap. |
| External Integration | Difficult/Unreliable | Reliable and programmatic invocation via CLI. | High: The proposed contract is the solution. |
| CLI Contract Documentation | Potentially missing or inconsistent | Clear, documented contract for external callers. | Moderate: New documentation required. |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Breaking existing interactive CLI usage | 🟡 Medium | 🔴 High | 6 | Implement headless mode via a dedicated `--auto` flag to isolate it from interactive mode. Thoroughly test both modes. |
| Inconsistent JSON schema or exit codes | 🟡 Medium | 🔴 High | 6 | Define strict JSON schemas for success and failure. Implement helper functions for standardized JSON output and exit code setting. Test across all relevant actions. |
| External integrations fail due to unstable contract | 🟡 Medium | 🔴 High | 6 | Document the contract comprehensively with examples. Coordinate with `Zenith` if possible. Ensure stability through rigorous testing. |
| Actions not designed for headless calls (e.g., relying on prompts) | 🟡 Medium | 🔴 High | 6 | Identify and refactor actions that require interactive prompts to accept parameters or default values programmatically. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|--------|--------|--------------|
| Requirement | ✅ Clear | Feature addresses a critical need for external integration and automation. |
| Feature | ✅ Defined | Scope and acceptance criteria are well-defined based on the issue. |
| Impact | ⚠️ Medium | Significant changes to `main.py` and documentation; moderate risk to existing interactive CLI if not handled carefully. |
| Feasibility | ✅ Feasible | Technically straightforward using standard Python libraries. |
| Security | ⚠️ Needs Review | Actions invoked via CLI must be robust against insecure input and avoid exposing secrets. |
| Performance | ✅ Acceptable | Minimal performance impact expected for argument parsing and dispatch. |
| Risk | ⚠️ Some Risks | Key risks include breaking interactive mode, ensuring output consistency, and action compatibility, all of which are mitigatable. |

### 9.2 Recommendations

1.  **Isolate Headless Mode:** Implement headless functionality using a distinct flag (e.g., `--auto`) to ensure the existing interactive CLI behavior remains unchanged and stable.
2.  **Standardize Outputs:** Define and enforce strict JSON schemas for both success and error responses. Ensure consistent use of non-zero exit codes for all failure conditions.
3.  **Adapt Actions:** Proactively review and refactor Luma CLI actions to support programmatic invocation, removing dependencies on interactive user input where necessary.
4.  **Document Contract:** Create clear, comprehensive documentation detailing the headless CLI arguments, expected JSON structures, and exit code conventions.

### 9.3 Next Steps

- [ ] Implement argument parsing for `--auto`, `--action`, `--json`, and `--project` in `main.py`.
- [ ] Modify `main.py` to conditionally execute actions based on the `--action` flag when `--auto` is present.
- [ ] Develop utility functions for generating consistent JSON output for success and failure scenarios.
- [ ] Implement logic to set appropriate exit codes (0 for success, non-zero for failure).
- [ ] Refactor specific Luma CLI actions (e.g., `code_review`) to be directly callable with parameters, if they currently rely on interactive prompts.
- [ ] Create or update `README.md` (or a dedicated CLI documentation file) to detail the new headless contract.
- [ ] Write unit tests covering headless invocation, JSON output, exit codes, and regression testing for interactive mode.

---

## 📎 Appendix

### Related Documents

- GitHub Issue #27: Add a headless CLI contract for external callers (--auto, --action, --json)

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Senior Technical Analyst | 2 เมษายน 2026 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |