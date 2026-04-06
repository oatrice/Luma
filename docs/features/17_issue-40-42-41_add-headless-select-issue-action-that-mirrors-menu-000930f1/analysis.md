# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Headless Issue Selection, First-Class Issue Creation, and Guided Workflow Orchestration |
| **Date** | 2026-04-06 |
| **Analyst** | Senior Technical Analyst |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |
| **Issue URL** | N/A |
| **Cross-Repository Scope** | Luma |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

*   **Issue #40**: The current headless CLI contract in Luma is limited to `code_review`, preventing external callers from automating the essential "Select Issue" interactive workflow. This workflow involves more than just selecting an issue; it also synchronizes roadmap context, transitions Luma's state to 'coding', and creates or switches the git branch for the selected issue.
*   **Issue #42**: Creating a GitHub issue is a fundamental task for project management but is currently nested within the `Update Roadmap` flow (via the `new` path) and is not exposed as a first-class Luma action or available through the headless contract. This lack of direct exposure makes issue creation harder to discover and automate.
*   **Issue #41**: While Luma offers a comprehensive interactive "Auto Full Workflow" that orchestrates issue selection, planning, coding, review, and CI handoff, this entire process is not mirrored by a corresponding headless action. External callers are limited to the narrow `code_review` capability, preventing them from automating the full development lifecycle.

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | External caller | Use a headless action to select Kanban issues and bootstrap the corresponding git branch and Luma state | I can automate the initial setup of a development task via the CLI. |
| 2 | User | Create a GitHub issue directly via a first-class Luma action | It is discoverable and easy to use within the Luma CLI interface. |
| 3 | External caller | Create a GitHub issue via a headless action with machine-readable results | I can automate issue creation and integrate it into other CI/CD or automation pipelines. |
| 4 | External caller | Orchestrate the full Luma guided workflow via a headless action | I can automate the entire development lifecycle from issue selection to CI follow-up programmatically. |

### 1.3 Acceptance Criteria

*   [ ] A new headless action exists for issue selection and branch bootstrap.
*   [ ] The issue selection action reuses the same selection constraints as the interactive Kanban flow.
*   [ ] The issue selection action creates or switches to the expected branch using the same rules as the current interactive implementation.
*   [ ] The issue selection action updates Luma state consistently (e.g., `active_issues`, `active_branch`).
*   [ ] The issue selection action returns a machine-readable JSON payload describing the selected issue(s), branch name, and resulting state, preserving the headless JSON stdout contract.
*   [ ] Issue creation is discoverable as a first-class action in Luma.
*   [ ] The issue creation flow does not rely on entering `new` inside the roadmap updater.
*   [ ] The created issue body supports repo conventions such as a `## Related` section.
*   [ ] If a headless action for issue creation is added, it preserves JSON stdout guarantees and returns the created issue number/URL.
*   [ ] A headless guided workflow action exists or there is a documented resumable headless orchestration equivalent to `Menu A` ("Auto Full Workflow").
*   [ ] The headless guided workflow action emits structured machine-readable status for each major workflow phase.
*   [ ] The headless guided workflow action can resume from existing state/checklist data instead of restarting blindly.
*   [ ] The new headless actions do not regress the current interactive `Menu 2` (Select Issue) flow.
*   [ ] Tests cover the interactive and/or headless contract behavior that is added for all new actions.

---

## 2. Feature Analysis

### 2.1 User Flow

*   **Issue #40 (Headless Select Issue):**
    ```mermaid
    flowchart TD
        A[External Caller] --> B(Call `main.py --action select_issue --params <issue_ids>`)
        B --> C{Luma Core}
        C --> D[Validate Issue IDs & Status]
        D --> E[Suggest/Create Branch]
        E --> F[Update Luma State]
        F --> G[Return JSON Payload]
        G --> H[External Caller Receives Payload]
    ```
*   **Issue #42 (First-Class/Headless Create Issue):**
    *   Interactive:
        ```mermaid
        flowchart TD
            A[User] --> B(Run `python main.py`)
            B --> C[Select "Create Issue" Action]
            C --> D[Input Issue Details (Title, Body, Project, etc.)]
            D --> E[Create GitHub Issue]
            E --> F[Update Luma State (if applicable)]
            F --> G[Display Result (Issue #/URL)]
        ```
    *   Headless:
        ```mermaid
        flowchart TD
            A[External Caller] --> B(Call `main.py --action create_issue --params <issue_details>`)
            B --> C{Luma Core}
            C --> D[Validate Input Details]
            D --> E[Create GitHub Issue]
            E --> F[Update Luma State]
            F --> G[Return JSON Payload (Issue #/URL, State)]
            G --> H[External Caller Receives Payload]
        ```
*   **Issue #41 (Headless Guided Workflow):**
    ```mermaid
    flowchart TD
        A[External Caller] --> B(Call `main.py --action guided_workflow --params <options>`)
        B --> C{Luma Core}
        C --> D[Initialize Workflow]
        D --> E[Execute Phase 1 (e.g., Issue Selection)]
        E --> F{Checkpoint/State?}
        F -->|Resume| G[Resume Workflow from State]
        F -->|Continue| H[Execute Next Phase]
        H --> I{Checkpoint/State?}
        I --> G
        I --> J[Return Structured JSON Progress/Result]
        J --> K[External Caller Receives Payload]
    ```

### 2.2 Screen/Page Requirements

> [!IMPORTANT]
> **Policy**: Web Full Implementation must be implemented and verified FIRST before Android/iOS logic.

N/A - These features are primarily for headless/CLI interaction, not direct UI screens.

| หน้าจอ | Actions | Components | UI Mock Status |
|--------|---------|------------|----------------|
| N/A | N/A | N/A | N/A |

### 2.3 Input/Output Specification

#### Inputs

*   **Issue #40 (Headless Select Issue):**
    *   `action`: `select_issue` (string, required)
    *   `issue_ids`: List of issue IDs or project card IDs (list of strings/integers, required)
    *   `context_repo`: Optional repository context if not implied. (string, optional)
*   **Issue #42 (Headless Create Issue):**
    *   `action`: `create_issue` (string, required)
    *   `title`: Title for the new issue (string, required)
    *   `body`: Body content for the issue (string, optional) - Should include `## Related` if not empty.
    *   `project_board_id`: Optional GitHub Project board ID for linking (string, optional)
    *   `project_column_id`: Optional GitHub Project column ID (string, optional)
    *   `repo`: Target repository (string, required, e.g., `owner/repo`)
    *   `issue_metadata`: Dict for additional metadata like labels, assignees etc. (dict, optional)
*   **Issue #41 (Headless Guided Workflow):**
    *   `action`: `guided_workflow` (string, required)
    *   `resume_state`: Optional state data to resume from (dict, optional)
    *   `workflow_options`: Parameters to customize workflow (e.g., issue selection criteria, model choices) (dict, optional)

#### Outputs

*   **Issue #40 (Headless Select Issue):**
    *   `selected_issues`: List of details for selected issues (list of dicts, required)
    *   `active_branch`: Name of the created/switched branch (string, required)
    *   `current_state`: Updated Luma state object (dict, required)
    *   `status`: "success" or "failure" (string, required)
    *   `message`: Descriptive message (string, optional)
*   **Issue #42 (Headless Create Issue):**
    *   `created_issue_number`: Number of the created issue (integer, required)
    *   `created_issue_url`: URL of the created issue (string, required)
    *   `current_state`: Updated Luma state object (dict, required)
    *   `status`: "success" or "failure" (string, required)
    *   `message`: Descriptive message (string, optional)
*   **Issue #41 (Headless Guided Workflow):**
    *   `workflow_progress`: Structured progress for each phase (dict, required, e.g., `{"issue_selection": {"status": "completed", "result": {...}}, "planning": {"status": "in_progress", "checkpoint": {...}}}`)
    *   `current_state`: Updated Luma state object (dict, required)
    *   `status`: "success", "failed", "interrupted" (string, required)
    *   `message`: Descriptive message (string, optional)

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `main.py` | 🔴 High | Will be modified to register and dispatch the new headless actions (`select_issue`, `create_issue`, `guided_workflow`). |
| `luma_core/actions/issue_actions.py` | 🔴 High | Will likely need modification to add the headless `select_issue` logic and potentially the first-class `create_issue` action. |
| `luma_core/actions/workflow_actions.py` | 🔴 High | Will need modification to add the headless `guided_workflow` action, potentially reusing or adapting `action_guided_workflow`. |
| `luma_core/actions/quality_actions.py` | 🟡 Medium | May be affected if issue creation logic is refactored out to `issue_actions.py`. |
| `luma_core/state_manager.py` | 🟡 Medium | State updates for `active_issues`, `active_branch`, etc., will need to be handled consistently across interactive and headless modes for new actions. |
| `luma_core/tools.py` | 🟢 Low | Potentially new utility functions for branch suggestion/creation or issue metadata handling may be introduced. |
| `tests/` | 🔴 High | New unit and integration tests will be required for all new headless and interactive actions to ensure correctness and prevent regressions. |
| Configuration Files (e.g., `.env`) | 🟢 Low | No direct impact expected, but LLM configuration might be relevant for workflow agents. |

### 3.2 Breaking Changes

*   [ ] **BC1:** Changes to the structured output of the `guided_workflow` headless action (Issue #41) might break existing external callers if they relied on a simpler or different output format than the new machine-readable checkpoints.
*   [ ] **BC2:** If the `create_issue` logic is moved or significantly altered from its nested location in `quality_actions.py` (Issue #42), existing internal integrations relying on that specific path might be affected.

### 3.3 Backward Compatibility Plan

```
- For the headless `select_issue` action (Issue #40), ensure the existing interactive `Menu 2` flow remains unaffected. The new headless action should aim for functional parity without altering the interactive experience.
- For the `create_issue` action (Issue #42), the existing nested flow within `Update Roadmap` should remain functional until it can be explicitly deprecated or removed. New integrations should use the first-class or headless action.
- For the headless `guided_workflow` action (Issue #41), if the previous headless contract only supported `code_review`, new actions can be added without breaking existing users. If `guided_workflow` was implicitly part of a broader headless capability, its new structured output must be handled gracefully by any consumers, or compatibility measures should be put in place. The prompt emphasizes preserving JSON stdout contract compatibility.
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python 3.9+, existing Luma libraries, GitHub CLI/API, and LLM integrations are suitable for implementing these headless actions. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | The project context indicates Luma has core components for state management, actions, and agent integration, suggesting the team possesses the necessary skills. |
| Infrastructure รองรับหรือไม่? | ✅ | No new infrastructure is explicitly required. Existing CI/CD and GitHub integration should suffice for these functional extensions. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 2-3 weeks |
| **Deadline** | N/A |
| **Buffer Time** | 3-5 days |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| N/A | N/A | No budget information provided. |
| **Total** | N/A | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| API Keys (GitHub, LLM) | 🔴 Critical | Access Control, Environment Variables (`.env` file). Existing protection mechanisms are sufficient; no new sensitive data handling is introduced. |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Input Validation for Headless Actions | 🔴 High | Implement robust input validation and sanitization for all parameters passed to headless actions (`select_issue`, `create_issue`, `guided_workflow`). Ensure adherence to GitHub API rate limits. |
| LLM Prompt Injection | 🟡 Medium | Sanitize inputs used in any LLM prompts triggered by these actions. Follow Luma's established LLM security practices. |

### 5.3 Authentication & Authorization

```
Headless actions will rely on the authenticated GitHub CLI (`gh`) and potentially LLM API keys configured in the environment. Authorization checks for GitHub actions (e.g., repository access, permissions to create issues/branches) will be handled by the underlying GitHub CLI or API calls, inheriting existing Luma authentication mechanisms.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| N/A | N/A | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| N/A | N/A | N/A |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Headless CLI Contract | Limited to `code_review`. Cannot automate core workflow bootstrapping or full lifecycle. | Extensible: Supports `select_issue`, `create_issue`, and a comprehensive `guided_workflow` with structured output. | The current headless contract is too narrow, preventing end-to-end automation of common Luma workflows. |
| Issue Creation Discoverability | Hidden within "Update Roadmap" flow, not a first-class action or headless option. | First-class interactive action and a dedicated headless action available. | Issue creation is not easily discoverable or automatable. |
| Workflow Orchestration | Interactive workflow is comprehensive, but headless counterpart is missing. | A machine-readable guided workflow action mimicking the interactive process is available. | The full power of Luma's interactive workflow orchestration is not accessible programmatically. |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Inconsistent State Management between Interactive and Headless Flows | 🟡 Medium | 🔴 High | 6 | Implement comprehensive unit and integration tests covering state transitions for both interactive and headless executions of new actions. Leverage shared logic where possible. |
| Regression in Existing Interactive Flows | 🟡 Medium | 🔴 High | 6 | Rigorously test existing interactive flows (`Menu 2`, `Auto Full Workflow`, nested issue creation) after implementing new headless counterparts. Rely on existing test suites. |
| Breaking Changes to Headless Contract for Issue #41 | 🟢 Low | 🟡 Medium | 2 | Clearly document the new structured output for `guided_workflow`. Implement compatibility for the old `code_review` output for a transition period if feasible, or ensure consumers are aware of changes. |
| Incomplete or Malformed Issue Creation/Metadata | 🟡 Medium | 🟡 Medium | 4 | Implement strict input validation for all parameters of the `create_issue` action. Ensure required fields like `title` and `repo` are present and validated. Enforce `## Related` section creation. |
| GitHub API Rate Limit Exceeded by New Actions | 🟢 Low | 🟡 Medium | 2 | Monitor API usage. If new headless actions are used in bulk, implement rate limiting strategies within Luma or advise users on usage management. Leverage existing Luma rate limiting mechanisms. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|--------|--------|--------------|
| Requirement | ✅ Clear | Clear requirements to expand Luma's headless CLI capabilities for issue selection, creation, and full workflow orchestration. |
| Feature | ✅ Defined | Well-defined features addressing key gaps in Luma's automation and discoverability. |
| Impact | ⚠️ Medium | Medium impact, primarily on `main.py` and core action modules, requiring careful integration and testing to avoid regressions. |
| Feasibility | ✅ Feasible | Technically and practically feasible with the current Luma stack. |
| Security | ⚠️ Needs Review | Low new security risk; existing mechanisms apply, with emphasis on input validation for headless actions. |
| Performance | ✅ Acceptable | No direct performance degradation expected; depends on underlying services (GitHub API, LLMs). |
| Risk | ⚠️ Some Risks | Medium risks identified, mainly concerning state consistency and potential regressions, which can be mitigated through thorough testing. |

### 9.2 Recommendations

1.  **Prioritize Headless Contract Parity**: Implement the new headless actions with a strong focus on mirroring the functionality and state transitions of their interactive counterparts to ensure a consistent user experience.
2.  **Robust Testing Strategy**: Develop comprehensive unit and integration tests for all new headless actions, covering success, failure, and state management scenarios. Crucially, include regression tests for existing interactive flows.
3.  **Clear Documentation**: Update Luma's documentation for the headless contract to clearly outline the new actions, their parameters, expected inputs, and machine-readable outputs.
4.  **Iterative Rollout**: Consider rolling out the headless `select_issue` and `create_issue` actions first, followed by the more complex `guided_workflow`, to manage development effort and gather feedback effectively.

### 9.3 Next Steps

*   [ ] Implement headless `select_issue` action.
*   [ ] Implement first-class interactive and headless `create_issue` actions.
*   [ ] Implement headless `guided_workflow` action with structured output.
*   [ ] Write comprehensive unit and integration tests for all new actions.
*   [ ] Update `main.py` to expose new headless actions.
*   [ ] Update Luma CLI documentation.

---

## 📎 Appendix

### Related Documents

*   [Luma Project README](README.md)
*   [Luma Headless Contract Notes](main.py - (implied))
*   [Issue Selection Logic](luma_core/actions/issue_actions.py - (implied))
*   [Guided Workflow Logic](luma_core/actions/workflow_actions.py::action_guided_workflow - (implied))

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Senior Technical Analyst | 2026-04-06 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |