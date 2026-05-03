# SBE (Specification by Example) Template

> 📅 Created: 2026-05-03
> 🔗 Issue: https://gitlab.com/oatricedev/Luma/-/issues/93

---

## Feature: VCS CLI Priority in PR Status Checking

ฟังก์ชัน check_pr_status_unified() และฟังก์ชันที่เกี่ยวข้องต้องใช้ VCS_CLI configuration เป็นลำดับความสำคัญสูงสุดในการตัดสินใจเลือก CLI tool สำหรับตรวจสอบสถานะ PR/MR โดยยังคงรักษา backward compatibility ผ่าน URL regex fallback

### Scenario: VCS_CLI=glab with GitHub PR URL - Happy Path

**Given** VCS_CLI=glab ใน config.py และมี GitHub PR URL https://github.com/oatrice/Cerebro/pull/65
**When** check_pr_status_unified() ถูกเรียกด้วย GitHub PR URL
**Then** ต้องใช้ glab CLI ในการตรวจสอบสถานะ และส่งคืนผลลัพธ์ที่ถูกต้อง

#### Examples

| VCS_CLI | PR URL | Expected CLI Tool | Expected Result |
|---------|--------|-------------------|-----------------|
| glab | https://github.com/oatrice/Cerebro/pull/65 | glab | {"merged": false, "state": "open", "error": None} |
| glab | https://github.com/facebook/react/pull/12345 | glab | {"merged": true, "state": "merged", "error": None} |
| glab | https://github.com/microsoft/vscode/pull/9999 | glab | {"merged": false, "state": "closed", "error": None} |

---

### Scenario: VCS_CLI=glab with GitLab MR URL - Happy Path

**Given** VCS_CLI=glab ใน config.py และมี GitLab MR URL https://gitlab.com/oatricedev/Luma/-/merge_requests/93
**When** check_pr_status_unified() ถูกเรียกด้วย GitLab MR URL
**Then** ต้องใช้ glab CLI ในการตรวจสอบสถานะ และส่งคืนผลลัพธ์ที่ถูกต้อง

#### Examples

| VCS_CLI | MR URL | Expected CLI Tool | Expected Result |
|---------|--------|-------------------|-----------------|
| glab | https://gitlab.com/oatricedev/Luma/-/merge_requests/93 | glab | {"merged": false, "state": "opened", "error": None} |
| glab | https://gitlab.com/gitlab-org/gitlab/-/merge_requests/456 | glab | {"merged": true, "state": "merged", "error": None} |
| glab | https://gitlab.com/kubernetes/kubernetes/-/merge_requests/789 | glab | {"merged": false, "state": "closed", "error": None} |

---

### Scenario: VCS_CLI=gh with GitHub PR URL - Fallback Behavior

**Given** VCS_CLI=gh ใน config.py และมี GitHub PR URL https://github.com/oatrice/Cerebro/pull/65
**When** check_pr_status_unified() ถูกเรียกด้วย GitHub PR URL
**Then** ต้องใช้ gh CLI ในการตรวจสอบสถานะ ตามการตั้งค่า VCS_CLI

#### Examples

| VCS_CLI | PR URL | Expected CLI Tool | Expected Result |
|---------|--------|-------------------|-----------------|
| gh | https://github.com/oatrice/Cerebro/pull/65 | gh | {"merged": false, "state": "open", "error": None} |
| gh | https://github.com/facebook/react/pull/12345 | gh | {"merged": true, "state": "merged", "error": None} |
| gh | https://github.com/microsoft/vscode/pull/9999 | gh | {"merged": false, "state": "closed", "error": None} |

---

### Scenario: VCS_CLI=gh with GitLab MR URL - URL Fallback

**Given** VCS_CLI=gh ใน config.py และมี GitLab MR URL https://gitlab.com/oatricedev/Luma/-/merge_requests/93
**When** check_pr_status_unified() ถูกเรียกด้วย GitLab MR URL
**Then** ต้อง fallback ไปใช้ URL regex matching และเลือก glab CLI

#### Examples

| VCS_CLI | MR URL | Expected CLI Tool | Expected Result |
|---------|--------|-------------------|-----------------|
| gh | https://gitlab.com/oatricedev/Luma/-/merge_requests/93 | glab | {"merged": false, "state": "opened", "error": None} |
| gh | https://gitlab.com/gitlab-org/gitlab/-/merge_requests/456 | glab | {"merged": true, "state": "merged", "error": None} |
| gh | https://gitlab.com/kubernetes/kubernetes/-/merge_requests/789 | glab | {"merged": false, "state": "closed", "error": None} |

---

### Scenario: VCS_CLI unset with both URL types - Default Behavior

**Given** VCS_CLI ไม่ได้ถูกตั้งค่า (unset) ใน config.py
**When** check_pr_status_unified() ถูกเรียกด้วย PR/MR URL ใดๆ
**Then** ต้อง fallback ไปใช้ URL regex matching เหมือนพฤติกรรมปัจจุบัน

#### Examples

| VCS_CLI | URL | Expected CLI Tool | Expected Result |
|---------|-----|-------------------|-----------------|
| (unset) | https://github.com/oatrice/Cerebro/pull/65 | gh | {"merged": false, "state": "open", "error": None} |
| (unset) | https://gitlab.com/oatricedev/Luma/-/merge_requests/93 | glab | {"merged": false, "state": "opened", "error": None} |
| (unset) | https://github.com/facebook/react/pull/12345 | gh | {"merged": true, "state": "merged", "error": None} |
| (unset) | https://gitlab.com/gitlab-org/gitlab/-/merge_requests/456 | glab | {"merged": true, "state": "merged", "error": None} |

---

## Notes

- VCS_CLI configuration มีค่าที่เป็นไปได้: "gh", "glab", หรือ unset (default: "gh")
- เมื่อ VCS_CLI=glab จะบังคับใช้ glab สำหรับทุก URL ทั้ง GitHub และ GitLab
- เมื่อ VCS_CLI=gh จะใช้ gh สำหรับ GitHub URL แต่ fallback ไป glab สำหรับ GitLab URL
- เมื่อ VCS_CLI unset จะใช้ URL regex matching เหมือนพฤติกรรมเดิม
- ฟังก์ชัน get_open_pr_unified() และ update_pull_request_unified() ต้องทำงานแบบเดียวกัน