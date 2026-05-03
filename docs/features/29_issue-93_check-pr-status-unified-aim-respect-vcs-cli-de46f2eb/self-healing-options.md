# Self-Healing Options for VCS_CLI Mismatch

> **Current Behavior**: Return error and stop execution  
> **Proposed**: Add self-healing mechanisms with user control

---

## 🔄 **Option 1: Automatic Fallback with Warning**

เมื่อ VCS_CLI mismatch ให้ fallback ไป URL regex matching และแสดง warning:

```python
if VCS_CLI == "glab":
    gitlab_match = re.match(r'https://gitlab\.com/([^/]+)/([^/]+)/-/merge_requests/(\d+)', pr_url)
    if gitlab_match:
        logger.debug("Using glab CLI (VCS_CLI=glab + GitLab URL)")
        return _check_pr_with_glab(pr_url)
    else:
        logger.warning("VCS_CLI=glab but GitHub URL provided - falling back to URL regex matching")
        return _check_pr_by_url_regex(pr_url)  # Self-healing
```

**Pros:**
- ✅ ไม่ break workflow
- ✅ ยังคง respect VCS_CLI เมื่อ match
- ✅ แสดง warning ให้ user รู้

**Cons:**
- ❌ อาจสร้าง confusion (VCS_CLI=glab แต่ใช้ gh)
- ❌ ทำให้ user ไม่ได้เรียนรู้ถึง configuration issue

---

## 🤖 **Option 2: Smart Auto-Detection**

ตรวจสอบ URL และ auto-switch CLI tool พร้อมแจ้ง user:

```python
if VCS_CLI == "glab":
    github_match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if github_match:
        logger.warning("VCS_CLI=glab but GitHub URL detected - auto-switching to gh CLI")
        return _check_pr_with_gh(pr_url)  # Self-healing with notification
```

**Pros:**
- ✅ ไม่ break workflow
- ✅ แจ้ง user ถึง auto-switch
- ✅ ทำงานได้จริง

**Cons:**
- ❌ ทำลายความตั้งใจของ VCS_CLI configuration
- ❌ อาจสร้างผลลัพธ์ที่ไม่คาดคิด

---

## ⚙️ **Option 3: Configuration Validation & Suggestion**

ตรวจสอบ VCS_CLI configuration และแนะนำการตั้งค่า:

```python
def validate_vcs_cli_config(pr_url: str) -> tuple[str, str]:
    """Validate VCS_CLI config and suggest correction."""
    from .config import VCS_CLI
    
    if VCS_CLI == "glab":
        github_match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
        if github_match:
            return "error", "VCS_CLI=glab but GitHub URL provided. Consider setting VCS_CLI=gh"
    elif VCS_CLI == "gh":
        gitlab_match = re.match(r'https://gitlab\.com/([^/]+)/([^/]+)/-/merge_requests/(\d+)', pr_url)
        if gitlab_match:
            return "error", "VCS_CLI=gh but GitLab URL provided. Consider setting VCS_CLI=glab"
    
    return "ok", "Configuration valid"

# Usage in check_pr_status_unified
status, message = validate_vcs_cli_config(pr_url)
if status == "error":
    logger.error(message)
    return {"merged": False, "state": "unknown", "error": message}
```

**Pros:**
- ✅ แจ้งปัญหาอย่างชัดเจน
- ✅ แนะนำการแก้ไข
- ✅ รักษาความตั้งใจของ configuration

**Cons:**
- ❌ ยังคง break workflow
- ❌ ต้อง manual intervention

---

## 🎛️ **Option 4: User-Controlled Self-Healing**

เพิ่ม configuration flag สำหรับ self-healing behavior:

```python
# In config.py
VCS_CLI_SELF_HEAL = os.getenv("VCS_CLI_SELF_HEAL", "false").lower() == "true"

# In check_pr_status_unified
if VCS_CLI == "glab":
    github_match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if github_match:
        if VCS_CLI_SELF_HEAL:
            logger.warning("VCS_CLI=glab but GitHub URL - self-healing enabled, using gh CLI")
            return _check_pr_with_gh(pr_url)
        else:
            logger.error("VCS_CLI=glab but GitHub URL - self-healing disabled")
            return {"merged": False, "state": "unknown", "error": "VCS_CLI=glab but GitHub URL provided"}
```

**Pros:**
- ✅ User ควบคุมได้
- ✅ เลือกได้ระหว่าง strict vs flexible
- ✅ Backward compatibility

**Cons:**
- ❌ เพิ่มความซับซ้อน
- ❌ ต้อง configure เพิ่ม

---

## 🎯 **Recommended Approach: Option 4 (User-Controlled)**

**Implementation Plan:**

1. **Add VCS_CLI_SELF_HEAL environment variable**
2. **Default to strict mode** (current behavior)
3. **Enable self-healing** เมื่อ user ตั้งค่า `VCS_CLI_SELF_HEAL=true`
4. **Clear logging** แสดงว่ากำลัง self-heal

**Usage Examples:**

```bash
# Strict mode (current behavior)
export VCS_CLI=glab
# จะ return error เมื่อ mismatch

# Self-healing mode
export VCS_CLI=glab
export VCS_CLI_SELF_HEAL=true
# จะ fallback ไป URL regex matching เมื่อ mismatch
```

---

## 📋 **Decision Matrix**

| Approach | Workflow Continuity | User Control | Implementation Complexity | Recommendation |
|-----------|-------------------|--------------|--------------------------|----------------|
| Current (Error) | ❌ Break | ✅ Full | ✅ Simple | ✅ **Current** |
| Auto Fallback | ✅ Continue | ❌ None | ✅ Simple | ⚠️ Consider |
| Smart Detection | ✅ Continue | ❌ None | ⚠️ Medium | ❌ Avoid |
| Config Validation | ❌ Break | ✅ Full | ✅ Simple | ⚠️ Consider |
| **User-Controlled** | ✅ Continue | ✅ Full | ⚠️ Medium | ✅ **Recommended** |

---

## 🚀 **Next Steps**

ถ้าต้องการ implement self-healing:

1. **Add VCS_CLI_SELF_HEAL** to config.py
2. **Update all 4 functions** ให้รองรับ self-healing
3. **Add comprehensive logging** 
4. **Update tests** สำหรับ self-healing scenarios
5. **Update documentation** ใน manual verification guide

**คำถาม**: คุณต้องการ implement self-healing แบบไหน หรือจะคง current strict behavior ไว้?
