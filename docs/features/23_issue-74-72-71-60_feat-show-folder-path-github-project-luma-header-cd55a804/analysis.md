# Analysis Template

> 📋 วิเคราะห์ Feature ก่อนเริ่มพัฒนา

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Luma Header Enhancement & Menu Reorganization |
| **Date** | 2026-04-10 |
| **Analyst** | Luma AI Architect |
| **Priority** | 🟡 Medium |
| **Status** | 📝 Draft |
| **Issue URL** | #74, #72, #71, #60 |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

```
1. Users in worktrees can't easily see which original repo they're working on
2. Frequently used "Auto Full Workflow" option is hard to find in menu
3. AI Brain sync pulls unrelated issues, cluttering context
4. Version numbers need standardization to pre-release format
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer | See folder path in header | Know exactly where I'm working |
| 2 | Developer | See GitHub Project number | Understand project context |
| 3 | Developer | Access "Auto Full Workflow" quickly | Save time navigating menus |
| 4 | Developer | Have AI sync only relevant issues | Get clean, focused context |

### 1.3 Acceptance Criteria

- [ ] **AC1**: Header shows folder path (truncated if >40 chars)
- [ ] **AC2**: Header shows GitHub Project number from config
- [ ] **AC3**: Worktree projects show original repo name + "(worktree)"
- [ ] **AC4**: Menu option "A" appears in top 3 positions
- [ ] **AC5**: AI Brain sync filters by current project context
- [ ] **AC6**: All versions use 0.x.x format

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[Start Luma CLI] --> B{Is worktree?}
    B -->|Yes| C[Show: Project (worktree)]
    B -->|No| D[Show: Project]
    C --> E[Show Folder Path]
    D --> E
    E --> F[Show GH Project #]
    F --> G[Display Menu with A near top]
    G --> H[User selects action]
```

### 2.2 Screen/Page Requirements

| Screen | Actions | Components | UI Mock Status |
|--------|---------|------------|----------------|
| Header | Display project info | 📂📁🐙📍 | ✅ Done |
| Menu | Navigate options | [0,A,1,2...] | ⬜ Pending |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| project['path'] | string | ✅ | must exist |
| project['kanban_number'] | int | ❌ | > 0 |
| cwd | string | ✅ | valid path |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| project_display | string | Name + optional "(worktree)" |
| folder_path | string | Truncated path |
| gh_project | string | "Project #N" or None |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| luma_core/ui.py | 🔴 High | Header display logic |
| luma_core/tools.py | 🔴 High | New worktree functions |
| main.py | 🟡 Medium | Menu ordering |
| luma_core/actions/admin_actions.py | 🟡 Medium | AI Brain sync |

### 3.2 Breaking Changes

- [ ] **BC1**: None expected - additive changes only

### 3.3 Backward Compatibility Plan

```
All changes are additive. Existing behavior preserved if:
- Not in worktree → shows original project name
- No kanban_number → skips GH Proj line
- No path → shows "N/A"
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Git CLI available |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | Python + Git |
| Infrastructure รองรับหรือไม่? | ✅ | N/A - CLI tool |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 1-2 days |
| **Deadline** | Flexible |
| **Buffer Time** | 1 day |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Development | $0 | Internal |
| Testing | $0 | Existing framework |
| **Total** | $0 | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| Folder paths | 🟢 Normal | Already visible in prompt |
| Project names | 🟢 Normal | Public in GitHub |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Path injection | 🟢 Low | Path just displayed, not executed |

### 5.3 Authentication & Authorization

```
No auth changes - uses existing GitHub CLI authentication
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Header render | < 100ms | N/A |
| Git command | < 500ms | N/A |

### 6.2 Scalability Plan

| Scenario | Expected | Strategy |
|----------|----------|----------|
| Single user | 1 | Direct execution |
| Multiple worktrees | 5-10 | No impact |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Worktree detection | Not supported | Detect and display | Add function |
| Menu ordering | A at position 14 | A at top 3 | Reorder dict |
| AI sync filtering | All issues | Filtered issues | Add filter |
| Version format | Mixed | 0.x.x | Update files |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Circular import | 🔴 High | 🔴 High | 9 | Use lazy imports |
| Git command failure | 🟡 Medium | 🟡 Medium | 4 | Fallback behavior |
| Menu confusion | 🟡 Medium | 🟢 Low | 2 | Keep key bindings |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | Well defined issues |
| Feature | ✅ Defined | Scope is clear |
| Impact | 🟡 Medium | Multiple files touched |
| Feasibility | ✅ Feasible | Simple changes |
| Security | ✅ Acceptable | No new risks |
| Performance | ✅ Acceptable | Negligible impact |
| Risk | ⚠️ Some Risks | Circular import risk |

### 9.2 Recommendations

1. **Fix circular import first** - Use lazy import in display_header()
2. **Test worktree detection** - Verify in actual worktree environment
3. **Get user feedback** - On new menu ordering

### 9.3 Next Steps

- [ ] Implement worktree detection in tools.py
- [ ] Update ui.py with lazy import
- [ ] Reorder menu in main.py
- [ ] Add AI sync filtering
- [ ] Update version files

---

## 📎 Appendix

### Related Documents

- Issue #74: https://github.com/oatrice/Luma/issues/74
- Issue #72: https://github.com/oatrice/Luma/issues/72
- Issue #71: https://github.com/oatrice/Luma/issues/71
- Issue #60: https://github.com/oatrice/Luma/issues/60

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Luma AI | 2026-04-10 | ✅ |
| Tech Lead | - | - | ⬜ |
| PM | - | - | ⬜ |
