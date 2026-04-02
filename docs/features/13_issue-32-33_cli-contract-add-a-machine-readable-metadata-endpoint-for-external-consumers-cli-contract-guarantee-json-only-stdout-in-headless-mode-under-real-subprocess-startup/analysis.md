# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | CLI Contract: Machine-Readable Metadata Endpoint & Guaranteed JSON Output in Headless Mode |
| **Date** | April 2, 2026 |
| **Analyst** | Senior Technical Analyst |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |
| **Issue URL** | N/A |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
External callers, such as Zenith, require a stable and machine-readable way to verify Luma's revision, contract version, and supported actions before executing tasks. This is crucial for compatibility checks and pinning specific Luma versions. Currently, Luma's headless mode, when used with JSON output, may still produce diagnostic text on stdout, which breaks consumers that rely on stdout exclusively for machine-readable data.
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | External consumer (e.g., Zenith) | Query Luma for machine-readable metadata (version, git commit, contract version, supported actions, Python version) | Ensure compatibility and pin Luma to a specific revision before executing actions. |
| 2 | External caller | Have Luma's headless `--json` mode output only parseable JSON on stdout, with all diagnostics, warnings, and logs routed to stderr | Reliably consume Luma's output in integration scripts without parsing errors caused by unexpected text. |

### 1.3 Acceptance Criteria

- [x] **AC1:** A single headless command (e.g., `luma --meta --json`) returns machine-readable metadata for external callers.
- [x] **AC2:** Zenith can use the metadata payload for compatibility and pin validation (supports https://github.com/oatrice/Zenith/issues/13).
- [x] **AC3:** Tests cover the metadata payload shape and failure handling.
- [x] **AC4:** Contract fields for metadata are documented for external integrations.
- [x] **AC5:** Headless `--json` mode produces parseable stdout under real subprocess execution.
- [x] **AC6:** Diagnostics, warnings, and logs do not corrupt the stdout payload in headless `--json` mode.
- [x] **AC7:** Tests verify stdout/stderr separation in real startup scenarios for headless `--json` mode.
- [x] **AC8:** The stdout/stderr contract for headless mode is documented for external consumers.

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[Start Luma CLI] --> B{Is Headless Mode Requested?};
    B -- Yes --> C{Is Metadata Requested?};
    B -- No --> D[Execute Interactive Workflow];
    C -- Yes --> E[Enable Metadata Mode];
    C -- No --> F[Execute Standard Headless Action];
    E --> G{Is JSON Output Specified?};
    G -- Yes --> H[Generate JSON Metadata Payload to STDOUT];
    G -- No --> I[Generate Default Metadata Output (e.g., text)];
    F --> J{Is JSON Output Specified?};
    J -- Yes --> K[Route Diagnostics to STDERR, JSON Action Output to STDOUT];
    J -- No --> L[Route Diagnostics to STDERR, Text Action Output to STDOUT];
    H --> M[End];
    I --> M;
    K --> M;
    L --> M;
    D --> M;
```

### 2.2 Screen/Page Requirements

> [!IMPORTANT]
> **Policy**: Web Full Implementation must be implemented and verified FIRST before Android/iOS logic.

| หน้าจอ | Actions | Components | UI Mock Status |
|--------|---------|------------|----------------|
| N/A (CLI Feature) | N/A | N/A | N/A |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `--meta` | flag | ❌ (Optional, enables metadata mode) | N/A |
| `--json` | flag | ❌ (Optional, specifies JSON output) | N/A |
| `--headless` | flag | Implicitly enabled when not running interactively; required for script execution. | N/A |

#### Outputs

**For `--meta --json` mode:**

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Luma application version (e.g., "1.6.0") |
| `git_commit` | string | Current Git commit hash of the Luma repository. |
| `dirty` | boolean | Indicates if the Git repository has uncommitted changes. |
| `contract_version` | string | Version of the Luma CLI contract for external integrations. |
| `supported_actions` | array of strings | List of all actions Luma can perform. |
| `python_version` | string | Version of Python Luma is running on (e.g., "3.9.18"). |

**For regular headless `--json` mode:**

| Field | Type | Description |
|-------|------|-------------|
| **STDOUT** | JSON | Parseable JSON output representing the result of the executed action. |
| **STDERR** | Text | Diagnostic messages, warnings, logs, and any non-JSON output. |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `main.py` | 🔴 High | Will be modified to parse new `--meta` and `--json` flags, and to route output based on these flags and execution context. |
| `luma_core/project_context.py` | 🟡 Medium | May need to be enhanced to provide Git commit hash, dirty status, and potentially `supported_actions` if not directly available elsewhere. |
| `luma_core/ui.py` | 🟡 Medium | Will require modifications to ensure strict separation of stdout and stderr for all headless JSON output. |
| `luma_core/config.py` | 🟢 Low | May need adjustments if configuration related to headless behavior or output formatting is centralized here. |
| `luma_core/actions/` | 🟢 Low | The `supported_actions` list must accurately reflect all actions available within the `actions/` directory. |
| Testing Infrastructure (`tests/`) | 🔴 High | New tests will be required for both the metadata endpoint (payload shape, fields) and the headless JSON output contract (stdout/stderr separation). |
| Documentation | 🔴 High | `README.md` and relevant contract documentation must be updated. |

### 3.2 Breaking Changes

- [x] **BC1:** The guarantee that headless `--json` mode outputs *only* parseable JSON on stdout will break existing integrations that might rely on parsing stdout which could contain diagnostic messages. Consumers will need to adapt to read stderr for diagnostics and ensure their parsing logic for stdout is robust.

### 3.3 Backward Compatibility Plan

```
For the metadata endpoint, this is a new feature and does not introduce backward compatibility concerns.

For the stdout/stderr separation in headless `--json` mode, this is a deliberate breaking change to ensure integration stability. External consumers will need to be aware of this new contract. Documentation will clearly outline this behavior. It is recommended that consumers of Luma's headless mode upgrade their integration logic to handle this separation. Older versions of Luma will not enforce this strict separation.
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python's `argparse` or similar libraries can handle new flags. Accessing Git information is achievable via `git` CLI commands or libraries like `gitpython`. Controlling stdout/stderr is a standard OS/Python capability. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | The Luma team has experience with Python CLI development, file I/O, and system interactions, which are sufficient for this task. |
| Infrastructure รองรับหรือไม่? | ✅ | Standard Python development environment and Git integration are already in place. No special infrastructure is required. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 2-3 days |
| **Deadline** | To be determined by project management. |
| **Buffer Time** | 1 day |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Development Time | Internal resource allocation | No direct external cost anticipated. |
| **Total** | N/A | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| `version` | 🟢 Normal | Informational. |
| `git_commit` | 🟢 Normal | Exposes internal build detail, but not typically considered sensitive unless linked to highly proprietary information. |
| `dirty` | 🟢 Normal | Indicates build status, not sensitive. |
| `contract_version` | 🟢 Normal | Informational. |
| `supported_actions` | 🟢 Normal | Informational. |
| `python_version` | 🟢 Normal | Informational. |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Command Injection | 🟡 Medium | Ensure all arguments passed to external processes (like `git` commands) are properly sanitized or use libraries that handle escaping. However, for simple flags like `--meta` and `--json`, this risk is low. |
| Information Disclosure | 🟢 Low | The exposed metadata is generally considered non-sensitive. If specific internal details were to be added in the future, re-evaluation would be necessary. |

### 5.3 Authentication & Authorization

```
The metadata endpoint should be accessible without authentication. It's intended for external callers to perform pre-flight checks before engaging with Luma. The existing Luma CLI execution context and any associated authentication for performing actions will still apply if an action is subsequently triggered.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Response Time (Metadata Endpoint) | < 50ms | N/A |
| Throughput (Metadata Endpoint) | High (as it's a lightweight operation) | N/A |
| Error Rate (Metadata Endpoint) | < 0.1% | N/A |
| STDOUT/STDERR Separation | Guaranteed clean STDOUT for JSON actions | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Normal | N/A (CLI tool) | The metadata endpoint is a stateless, lightweight operation and scales inherently. |
| Peak | N/A (CLI tool) | N/A |
| Growth (1yr) | N/A (CLI tool) | N/A |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Headless Output Contract | May contain mixed stdout/stderr, breaking JSON parsing. | Guaranteed JSON-only stdout for headless `--json` mode, with stderr for diagnostics. | Significant gap in integration reliability and predictable output. |
| Machine-Readable Metadata | No dedicated endpoint or standardized format for version/contract verification. | Dedicated `--meta --json` endpoint providing stable, machine-readable metadata. | Complete gap; no existing mechanism for external programmatic verification of Luma's state. |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Existing integrations break due to STDOUT/STDERR change | 🟡 Medium | 🔴 High | 6 | Implement strict separation, update documentation thoroughly, and communicate the change clearly. Advise users to update their parsing scripts. |
| Metadata payload not stable across Luma versions | 🟢 Low | 🟡 Medium | 2 | Define a clear `contract_version` and follow semantic versioning for the metadata contract. Document the contract fields clearly. |
| Difficulty in reliably fetching Git commit/dirty status | 🟢 Low | 🟢 Low | 1 | Use robust methods for Git interaction (e.g., `git` CLI via `subprocess` with proper error handling). |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | Both issues have clear problem statements and acceptance criteria. |
| Feature | ✅ Defined | The proposed features for metadata endpoint and headless JSON output are well-defined. |
| Impact | ⚠️ Medium | The stdout/stderr contract change is a breaking change for existing integrations. |
| Feasibility | ✅ Feasible | Technically straightforward with existing Python and Git tooling. |
| Security | ⚠️ Needs Review | Low sensitivity data, but command injection is a minor consideration. |
| Performance | ✅ Acceptable | Expected to be fast and reliable. |
| Risk | ⚠️ Some Risks | Primary risk is breaking existing integrations due to stdout/stderr changes. |

### 9.2 Recommendations

1.  **Implement `--meta --json` Flag:** Introduce a new command-line flag combination (`--meta --json`) to expose Luma's version, Git commit, contract version, supported actions, and Python version in a stable JSON format.
2.  **Enforce Strict Headless JSON Output:** Modify all headless operations that output JSON to guarantee that only parseable JSON is written to stdout. All diagnostic messages, logs, and warnings must be routed to stderr.
3.  **Update Documentation:** Clearly document the new metadata contract (fields, types, stability guarantees) and the refined headless JSON output contract (stdout/stderr separation) for external consumers.
4.  **Develop Comprehensive Tests:** Create robust unit and integration tests to cover the metadata payload structure, failure cases, and the correct separation of stdout and stderr in headless JSON mode.
5.  **Communicate Breaking Change:** Proactively inform users about the upcoming change in the headless JSON output contract, providing guidance on how to adapt their integrations.

### 9.3 Next Steps

- [ ] Implement the logic for retrieving and formatting metadata.
- [ ] Implement the `--meta` flag and integrate it with `main.py`.
- [ ] Refactor headless JSON output to enforce stdout/stderr separation.
- [ ] Write unit tests for metadata generation and headless JSON output.
- [ ] Write integration tests simulating external consumer scenarios.
- [ ] Update `README.md` and any relevant API documentation.
- [ ] Consider adding a `contract_version` to the Luma state or configuration.

---

## 📎 Appendix

### Related Documents

- [Link to PRD] (N/A)
- [Link to Design Docs] (N/A)
- [Link to API Specs] (Will be generated by documentation update)
- Related Issues: Zenith #13, Luma #27, Luma #29

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Senior Technical Analyst | April 2, 2026 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |