# Specification: check_pr_status_unified() ไม่ respect VCS_CLI configuration

> **Status**: Proposed
> **Owner**: Luma Development Team
> **Dates**: Created: 2026-05-03 | Last Updated: 2026-05-03

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
ฟังก์ชัน check_pr_status_unified() ใน luma_core/platform_detector.py ใช้ URL regex matching เพื่อเลือก CLI tool (GitHub URLs → gh, GitLab URLs → glab) โดยไม่พิจารณา VCS_CLI configuration จาก config.py ซึ่งทำให้เกิดปัญหาเมื่อผู้ใช้ตั้งค่า VCS_CLI=glab แต่มี GitHub PR URL ใน .luma_state.json ระบบจะใช้ gh แทนที่จะใช้ glab ตาม configuration

### Goal
ทำให้ check_pr_status_unified() และฟังก์ชันที่เกี่ยวข้องใช้ VCS_CLI configuration เป็นลำดับความสำคัญสูงสุดในการตัดสินใจเลือก CLI tool โดยยังคงรักษา backward compatibility ผ่าน URL regex fallback

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **Luma User**, I want to **check_pr_status_unified() ให้ใช้ VCS CLI ตามที่ตั้งค่าไว้ใน VCS_CLI**, so that **การตรวจสอบสถานะ PR/MR สอดคล้องกับการตั้งค่าของผู้ใช้**

### Functional Requirements
- [ ] check_pr_status_unified() ต้องตรวจสอบ config.VCS_CLI ก่อน URL regex matching
- [ ] ถ้า VCS_CLI=glab ต้องใช้ glab สำหรับทุกการตรวจสอบ PR/MR
- [ ] ถ้า VCS_CLI=gh หรือ unset ให้ fallback ไปใช้ URL regex matching
- [ ] get_open_pr_unified() และ update_pull_request_unified() ต้องทำงานแบบเดียวกัน
- [ ] เพิ่ม logging เพื่อแสดงว่าใช้ CLI tool อะไร

### Non-Functional Requirements
- [ ] Performance: ไม่ควรช้ากว่าปัจจุบัน (>500ms)
- [ ] Security: ไม่เปิดช่องโหว่ใหม่ๆ
- [ ] Backward Compatibility: รักษาพฤติกรรมเดิมเมื่อ VCS_CLI=gh หรือ unset

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: VCS_CLI=glab with GitHub PR URL
**Given** VCS_CLI=glab ใน config และมี GitHub PR URL https://github.com/oatrice/Cerebro/pull/65
**When** check_pr_status_unified() ถูกเรียก
**Then** ต้องใช้ glab ในการตรวจสอบสถานะ ไม่ใช่ gh

#### Examples
| VCS_CLI | PR URL | Expected CLI Tool |
|---------|--------|-------------------|
| glab | https://github.com/oatrice/Cerebro/pull/65 | glab |
| glab | https://gitlab.com/oatricedev/Luma/-/merge_requests/93 | glab |
| gh | https://github.com/oatrice/Cerebro/pull/65 | gh |
| (unset) | https://github.com/oatrice/Cerebro/pull/65 | gh |

### Scenario: VCS_CLI=gh with GitLab MR URL
**Given** VCS_CLI=gh ใน config และมี GitLab MR URL https://gitlab.com/oatricedev/Luma/-/merge_requests/93
**When** check_pr_status_unified() ถูกเรียก
**Then** ต้องใช้ glab ตาม URL regex matching (เพราะ VCS_CLI=gh ไม่บังคับใช้ gh)

#### Examples
| VCS_CLI | PR URL | Expected CLI Tool |
|---------|--------|-------------------|
| gh | https://gitlab.com/oatricedev/Luma/-/merge_requests/93 | glab |
| gh | https://github.com/oatrice/Cerebro/pull/65 | gh |
| (unset) | https://gitlab.com/oatricedev/Luma/-/merge_requests/93 | glab |
| (unset) | https://github.com/oatrice/Cerebro/pull/65 | gh |

---

## 4. Constraints & Risks
*What should we watch out for?*
- **Constraint 1**: ต้องรักษา backward compatibility สำหรับผู้ใช้ที่ไม่ได้ตั้งค่า VCS_CLI
- **Risk 1**: การเปลี่ยนพฤติกรรมอาจกระทบกรณี edge cases ที่ยังไม่เคยพบ
- **Risk 2**: ต้องแน่ใจว่า CLI tool ที่เลือกมี authentication เพียงพอ