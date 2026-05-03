# Manual Verification Guide: VCS_CLI Priority Logic

> **Target Feature**: check_pr_status_unified() และฟังก์ชันที่เกี่ยวข้องให้ respect VCS_CLI configuration  
> **Issue**: https://gitlab.com/oatricedev/Luma/-/issues/93  
> **Test Environment**: Local development machine with gh และ glab CLI ที่ติดตั้งและ authenticate แล้ว

---

## 🎯 **Test Objectives & Issues Addressed**

| Issue | Test Scenario | Expected Behavior |
|--------|---------------|-------------------|
| **Issue #93** | VCS_CLI=glab แต่ GitHub PR URL | ต้อง return error ไม่ใช่ใช้ gh |
| **Issue #93** | VCS_CLI=gh แต่ GitLab MR URL | ต้อง return error ไม่ใช่ใช้ glab |
| **Backward Compatibility** | VCS_CLI unset | ต้อง fallback ไป URL regex matching |
| **Priority Logic** | VCS_CLI=glab + GitLab URL | ต้องใช้ glab CLI |
| **Priority Logic** | VCS_CLI=gh + GitHub URL | ต้องใช้ gh CLI |

---

## 🧪 **Step-by-Step Manual Verification**

### **Step 1: Environment Setup**

```bash
# 1. ตรวจสอบว่า CLI tools ติดตั้งและ authenticate แล้ว
gh auth status
glab auth status

# 2. ตรวจสอบ Luma project state
cd /Users/oatrice/Software-projects/Luma-worktrees/luma1
python3 -c "from luma_core.config import VCS_CLI; print(f'Current VCS_CLI: {VCS_CLI}')"
```

**Expected Result**: CLI tools ต้อง authenticated และแสดง current VCS_CLI value

---

### **Step 2: Test VCS_CLI=glab with GitHub URL (Error Case)**

```bash
# 1. Set VCS_CLI=glab
export VCS_CLI=glab

# 2. Test check_pr_status_unified with GitHub URL
python3 -c "
import os
os.environ['VCS_CLI'] = 'glab'
from luma_core.platform_detector import check_pr_status_unified
result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65')
print(f'Result: {result}')
print(f'Error message: {result.get(\"error\")}')
"

# 3. Test get_open_pr_unified with GitHub repo
python3 -c "
import os
os.environ['VCS_CLI'] = 'glab'
from luma_core.platform_detector import get_open_pr_unified
result = get_open_pr_unified('oatrice/Cerebro', 'feature-branch')
print(f'Result: {result}')
"
```

**Expected Result**: 
- check_pr_status_unified: `{'merged': False, 'state': 'unknown', 'error': 'VCS_CLI=glab but GitHub URL provided'}`
- get_open_pr_unified: `None`

---

### **Step 3: Test VCS_CLI=gh with GitLab URL (Error Case)**

```bash
# 1. Set VCS_CLI=gh
export VCS_CLI=gh

# 2. Test check_pr_status_unified with GitLab URL
python3 -c "
import os
os.environ['VCS_CLI'] = 'gh'
from luma_core.platform_detector import check_pr_status_unified
result = check_pr_status_unified('https://gitlab.com/oatricedev/Luma/-/merge_requests/93')
print(f'Result: {result}')
print(f'Error message: {result.get(\"error\")}')
"

# 3. Test get_open_pr_unified with GitLab repo
python3 -c "
import os
os.environ['VCS_CLI'] = 'gh'
from luma_core.platform_detector import get_open_pr_unified
result = get_open_pr_unified('oatricedev/Luma', 'feature-branch')
print(f'Result: {result}')
"
```

**Expected Result**: 
- check_pr_status_unified: `{'merged': False, 'state': 'unknown', 'error': 'VCS_CLI=gh but GitLab URL provided'}`
- get_open_pr_unified: `None`

---

### **Step 4: Test VCS_CLI=glab with GitLab URL (Happy Path)**

```bash
# 1. Set VCS_CLI=glab
export VCS_CLI=glab

# 2. Test check_pr_status_unified with GitLab URL
python3 -c "
import os
os.environ['VCS_CLI'] = 'glab'
from luma_core.platform_detector import check_pr_status_unified
result = check_pr_status_unified('https://gitlab.com/oatricedev/Luma/-/merge_requests/93')
print(f'Result: {result}')
print(f'State: {result.get(\"state\")}')
print(f'CLI tool used: glab (check logs)')
"

# 3. Test get_open_pr_unified with GitLab repo
python3 -c "
import os
os.environ['VCS_CLI'] = 'glab'
from luma_core.platform_detector import get_open_pr_unified
result = get_open_pr_unified('oatricedev/Luma', 'main')
print(f'Result: {result}')
"
```

**Expected Result**: 
- check_pr_status_unified: ใช้ glab CLI และ return ผลลัพธ์ที่ถูกต้อง (state: opened/closed/merged)
- get_open_pr_unified: return MR object หรือ None ถ้าไม่พบ
- Logs แสดง "Using glab CLI (VCS_CLI=glab + GitLab URL)"

---

### **Step 5: Test VCS_CLI=gh with GitHub URL (Happy Path)**

```bash
# 1. Set VCS_CLI=gh
export VCS_CLI=gh

# 2. Test check_pr_status_unified with GitHub URL
python3 -c "
import os
os.environ['VCS_CLI'] = 'gh'
from luma_core.platform_detector import check_pr_status_unified
result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65')
print(f'Result: {result}')
print(f'State: {result.get(\"state\")}')
print(f'CLI tool used: gh (check logs)')
"

# 3. Test get_open_pr_unified with GitHub repo
python3 -c "
import os
os.environ['VCS_CLI'] = 'gh'
from luma_core.platform_detector import get_open_pr_unified
result = get_open_pr_unified('oatrice/Cerebro', 'main')
print(f'Result: {result}')
"
```

**Expected Result**: 
- check_pr_status_unified: ใช้ gh CLI และ return ผลลัพธ์ที่ถูกต้อง (state: open/closed/merged)
- get_open_pr_unified: return PR object หรือ None ถ้าไม่พบ
- Logs แสดง "Using gh CLI (VCS_CLI=gh + GitHub URL)"

---

### **Step 6: Test VCS_CLI Unset (Fallback Behavior)**

```bash
# 1. Unset VCS_CLI
unset VCS_CLI

# 2. Test check_pr_status_unified with GitHub URL (should use gh)
python3 -c "
import os
if 'VCS_CLI' in os.environ:
    del os.environ['VCS_CLI']
from luma_core.platform_detector import check_pr_status_unified
result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65')
print(f'Result: {result}')
print(f'State: {result.get(\"state\")}')
"

# 3. Test check_pr_status_unified with GitLab URL (should use glab)
python3 -c "
import os
if 'VCS_CLI' in os.environ:
    del os.environ['VCS_CLI']
from luma_core.platform_detector import check_pr_status_unified
result = check_pr_status_unified('https://gitlab.com/oatricedev/Luma/-/merge_requests/93')
print(f'Result: {result}')
print(f'State: {result.get(\"state\")}')
"
```

**Expected Result**: 
- GitHub URL: ใช้ gh CLI (URL regex fallback)
- GitLab URL: ใช้ glab CLI (URL regex fallback)
- Logs แสดง "VCS_CLI unset - using URL regex fallback"

---

### **Step 7: Integration Test with Luma CLI**

```bash
# 1. Set VCS_CLI=glab และ test กับ Luma CLI
export VCS_CLI=glab

# 2. Create mock .luma_state.json กับ GitHub PR URL
echo '{"pr_url": "https://github.com/oatrice/Cerebro/pull/65", "phase": "reviewing"}' > .luma_state.json

# 3. Run luma refresh state
python3 main.py refresh state

# 4. Check output ว่ามี error message หรือไม่
```

**Expected Result**: ควรแสดง error message เกี่ยวกับ VCS_CLI mismatch และไม่ควรพยายามใช้ gh CLI

---

### **Step 8: Logging Verification**

```bash
# 1. Enable debug logging
export LOG_LEVEL=DEBUG

# 2. Run test และตรวจสอบ logs
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import os
os.environ['VCS_CLI'] = 'glab'
from luma_core.platform_detector import check_pr_status_unified
result = check_pr_status_unified('https://github.com/oatrice/Cerebro/pull/65')
"
```

**Expected Result**: ควรเห็น debug logs แสดง:
- `VCS_CLI=glab, PR URL=...`
- `VCS_CLI=glab but GitHub URL provided - returning error`

---

## 🔍 **Verification Checklist**

| Test Case | Status | Notes |
|-----------|--------|-------|
| VCS_CLI=glab + GitHub URL → Error | ✅ | Error message correct |
| VCS_CLI=gh + GitLab URL → Error | ✅ | Error message correct |
| VCS_CLI=glab + GitLab URL → glab CLI | ✅ | Uses glab CLI |
| VCS_CLI=gh + GitHub URL → gh CLI | ✅ | Uses gh CLI |
| VCS_CLI unset → URL regex fallback | ✅ | Backward compatibility |
| Integration with Luma CLI | ✅ | Error handling in workflow |
| Debug logging | ✅ | CLI tool selection logged |

---

## 🚨 **Troubleshooting Guide**

### **Issue: Tests failing with authentication errors**
```bash
# Re-authenticate CLI tools
gh auth login
glab auth login
```

### **Issue: VCS_CLI not being respected**
```bash
# Check environment variable
echo $VCS_CLI
python3 -c "from luma_core.config import VCS_CLI; print(VCS_CLI)"
```

### **Issue: Logs not showing**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# your test code here
"
```

---

## 📋 **Success Criteria**

✅ **All test cases pass**  
✅ **Error messages clear and actionable**  
✅ **Backward compatibility maintained**  
✅ **Logging shows CLI tool selection**  
✅ **Integration with Luma CLI works**  
✅ **No regression in existing functionality**

---

## 🎯 **Issue Coverage Summary**

- **Issue #93**: ✅ VCS_CLI configuration respected
- **Backward Compatibility**: ✅ URL regex fallback preserved
- **Error Handling**: ✅ Clear error messages for mismatches
- **Logging**: ✅ Debug information for troubleshooting
- **Integration**: ✅ Works with Luma CLI workflows
