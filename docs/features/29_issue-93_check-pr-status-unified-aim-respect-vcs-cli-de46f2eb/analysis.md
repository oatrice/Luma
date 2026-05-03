# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | check_pr_status_unified() ไม่ respect VCS_CLI configuration |
| **Date** | 2026-05-03 |
| **Analyst** | Cascade AI |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |
| **Issue URL** | https://gitlab.com/oatricedev/Luma/-/issues/93 |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
ฟังก์ชัน check_pr_status_unified() ใน luma_core/platform_detector.py ใช้ URL regex matching เพื่อตัดสินใจว่าจะใช้ CLI tool อะไร (GitHub URLs → gh, GitLab URLs → glab) โดยไม่พิจารณา VCS_CLI configuration จาก config.py ซึ่งทำให้เกิดปัญหาเมื่อผู้ใช้ตั้งค่า VCS_CLI=glab แต่มี GitHub PR URL ใน .luma_state.json ระบบจะใช้ gh แทนที่จะใช้ glab ตาม configuration
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Luma User | check_pr_status_unified() ให้ใช้ VCS CLI ตามที่ตั้งค่าไว้ใน VCS_CLI | เพื่อให้การตรวจสอบสถานะ PR/MR สอดคล้องกับการตั้งค่าของผู้ใช้ |
| 2 | Luma User | VCS_CLI configuration มีผลกับทุกการดำเนินการ VCS | เพื่อความสม่ำเสมอในการใช้งาน CLI tool |

### 1.3 Acceptance Criteria

- [ ] **AC1:** check_pr_status_unified() ต้องตรวจสอบ config.VCS_CLI ก่อนใช้ URL regex matching
- [ ] **AC2:** ถ้า VCS_CLI=glab ต้องใช้ glab สำหรับทุกการตรวจสอบ PR/MR ไม่ว่า URL จะเป็น GitHub หรือ GitLab
- [ ] **AC3:** ถ้า VCS_CLI=gh หรือ unset ให้ fallback ไปใช้ URL regex matching เหมือนเดิม
- [ ] **AC4:** get_open_pr_unified() และ update_pull_request_unified() ต้องทำงานแบบเดียวกัน

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[User sets VCS_CLI=glab] --> B[GitHub PR URL in state]
    B --> C{check_pr_status_unified()}
    C -->|Current| D[Uses gh - WRONG]
    C -->|Desired| E[Uses glab - CORRECT]
    D --> F[Inconsistent behavior]
    E --> G[Consistent with config]
```

### 2.2 Screen/Page Requirements

> [!IMPORTANT]
> **Policy**: Web Full Implementation must be implemented and verified FIRST before Android/iOS logic.

| หน้าจอ | Actions | Components | UI Mock Status |
|--------|---------|------------|----------------|
| N/A | N/A | N/A | N/A (CLI Feature) |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| pr_url | string | ✅ | Valid GitHub/GitLab PR/MR URL |
| VCS_CLI | string | ❌ | "gh" or "glab" |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| merged | boolean | Whether PR/MR is merged |
| state | string | "open", "closed", "merged", "unknown" |
| error | string | Error message if any |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| luma_core/platform_detector.py | 🔴 High | ต้องแก้ไข check_pr_status_unified(), get_open_pr_unified(), update_pull_request_unified() |
| luma_core/config.py | 🟡 Medium | VCS_CLI configuration ถูกใช้งานอยู่แล้ว |
| tests/test_platform_detector.py | 🟡 Medium | ต้องเพิ่ม test cases ใหม่ |

### 3.2 Breaking Changes

- [ ] **BC1:** การเปลี่ยนลำดับการตรวจสอบอาจส่งผลต่อกรณี edge cases ที่ยังไม่เคยพบ
- [ ] **BC2:** ผู้ใช้ที่ตั้งค่า VCS_CLI=glab แต่มี GitHub PR URL จะเห็นการเปลี่ยนแปลงพฤติกรรม

### 3.3 Backward Compatibility Plan

```
- รักษา URL regex matching เป็น fallback เมื่อ VCS_CLI=gh หรือ unset
- ไม่เปลี่ยนแปลง signature ของฟังก์ชัน
- เพิ่ม logging เพื่อให้ผู้ใช้ทราบว่าใช้ CLI tool อะไร
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python 3.9+, VCS CLI wrappers มีอยู่แล้ว |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | การแก้ไข Python functions พื้นฐาน |
| Infrastructure รองรับหรือไม่? | ✅ | ไม่ต้องการ infrastructure ใหม่ |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 2-3 days |
| **Deadline** | N/A |
| **Buffer Time** | 1 day |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Development Time | 2-3 days | Internal resource |
| Testing | 0.5 day | Internal resource |
| **Total** | 2.5-3.5 days | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| VCS Tokens | 🔴 Critical | ใช้จาก environment variables อยู่แล้ว |
| PR URLs | 🟢 Normal | Public URLs |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| CLI Command Injection | 🟡 Medium | Validate URLs, use existing CLI wrapper |

### 5.3 Authentication & Authorization

```
ใช้ VCS_TOKEN จาก config.py อยู่แล้ว ไม่ต้องเปลี่ยนแปลง
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Response Time | < 500ms | ~200ms |
| Throughput | N/A | N/A |
| Error Rate | < 1% | < 1% |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Normal | 1-10 users | Single process |
| Peak | 10-50 users | Single process |
| Growth (1yr) | 50-100 users | Single process |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| CLI Selection | URL regex only | VCS_CLI priority + URL fallback | ต้องเพิ่ม VCS_CLI check |
| Consistency | Inconsistent with config | Consistent with VCS_CLI | ต้องแก้ไข logic |
| Testing | Basic tests | Comprehensive VCS_CLI tests | ต้องเพิ่ม test cases |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Breaking existing behavior | 🟡 Medium | 🔴 High | 6 | Fallback to URL regex when VCS_CLI=gh/unset |
| CLI tool not available | 🟡 Medium | 🟡 Medium | 4 | Better error messages, graceful fallback |
| Test coverage gaps | 🟢 Low | 🟡 Medium | 2 | Add comprehensive test cases |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | VCS_CLI should override URL detection |
| Feature | ✅ Defined | Simple logic change with fallback |
| Impact | ⚠️ Medium | Affects 3 functions, manageable |
| Feasibility | ✅ Feasible | Low complexity, high value |
| Security | ✅ Acceptable | No new security concerns |
| Performance | ✅ Acceptable | No performance impact |
| Risk | ⚠️ Some Risks | Mitigation plan in place |

### 9.2 Recommendations

1. **Implement VCS_CLI priority check** in check_pr_status_unified()
2. **Add comprehensive tests** for all VCS_CLI combinations
3. **Maintain backward compatibility** with URL regex fallback
4. **Update related functions** (get_open_pr_unified, update_pull_request_unified)

### 9.3 Next Steps

- [ ] Write failing tests for VCS_CLI behavior
- [ ] Implement VCS_CLI priority logic
- [ ] Update related functions
- [ ] Add comprehensive test coverage
- [ ] Manual verification with both CLI tools

---

## 📎 Appendix

### Related Documents

- [GitLab Issue #93](https://gitlab.com/oatricedev/Luma/-/issues/93)
- [luma_core/platform_detector.py](../../../luma_core/platform_detector.py)
- [luma_core/config.py](../../../luma_core/config.py)

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Cascade AI | 2026-05-03 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |