# Manual Verification Guide: Worktree Support for Select Issue & Code Review

> **Scope**: Verify worktree path resolution works correctly across all affected menu actions
> **Issues**: [#64](https://github.com/oatrice/Luma/issues/64), [#70](https://github.com/oatrice/Luma/issues/70)
> **Date**: 2026-04-10

---

## 📋 Verification Matrix

| Step | Scenario | Menu Action | Issue | Expected Result | Verification Method |
|------|----------|-------------|-------|-----------------|---------------------|
| 1 | Select Issue from worktree | `[2] 📥 Select Issue (from Kanban)` | #64 | Git branch created in worktree | Check `git branch` in worktree |
| 2 | Select Issue headless from worktree | Auto-workflow / Headless | #64 | Git branch created in worktree | Check `git branch` in worktree |
| 3 | Code Review from worktree | `[6] 🧐 Code Review (Local)` | #70 | Changes detected from worktree, report saved in worktree | Check `code_review.md` location |
| 4 | Update Docs from worktree | `[7] 📝 Update Docs` | #64 | CHANGELOG.md read from worktree | Check file paths in output |
| 5 | Update Roadmap from worktree | `[U] 🗺️ Update Roadmap` | #64 | ROADMAP.md read/written in worktree | Check file paths in output |
| 6 | Add Issue to session from worktree | `[+] ➕ Add Issue (to session)` | #64 | Git operations in worktree | Check `git branch` in worktree |
| 7 | Regression: Main repo still works | All actions | #64, #70 | Operations work in main repo (non-worktree) | Verify no regression |

---

## 🔬 Detailed Verification Steps

### Step 1: Select Issue from Worktree
**Issue**: #64 - Select Issue action ไม่รองรับ worktree path

**Preconditions**:
```bash
# Setup
 cd /path/to/main/repo
 git worktree add -b feat/test-worktree ../worktree-test
 cd ../worktree-test
```

**Action**:
1. Run `python main.py` from worktree directory
2. Select menu `[2] 📥 Select Issue (from Kanban)`
3. Select any issue
4. Select suggested branch or enter custom branch name

**Expected Output**:
```
🌿 Worktree detected: Using /path/to/worktree-test instead of /path/to/main/repo
🔄 Creating git branch...
✅ Branch 'feat/xxx-issue-name' created and checked out.
```

**Verification**:
```bash
# In worktree directory
git branch --show-current
# Expected: feat/xxx-issue-name

# In main repo directory
git branch --show-current
# Expected: main (or previous branch, NOT the new feature branch)
```

**Pass Criteria**: ✅ Feature branch exists only in worktree, NOT in main repo

---

### Step 2: Select Issue Headless from Worktree
**Issue**: #64 - _start_issues_headless() ไม่รองรับ worktree path

**Preconditions**:
```bash
cd /path/to/worktree-test
```

**Action**:
```bash
python main.py --auto --action bootstrap --issue 123
```

**Expected Output**:
```
   🌿 Worktree detected: Using /path/to/worktree-test instead of /path/to/main/repo
✅ Started (Headless): #123
🌿 Branch: feat/123-issue-name
🔄 Creating git branch...
✅ Branch 'feat/123-issue-name' created and checked out.
```

**Verification**:
```bash
git -C /path/to/worktree-test branch --show-current
# Expected: feat/123-issue-name

git -C /path/to/main/repo branch --show-current
# Expected: main (NOT feat/123-issue-name)
```

**Pass Criteria**: ✅ Branch created in worktree only

---

### Step 3: Code Review from Worktree
**Issue**: #70 - Code Review อ่าน change จาก main repo แทน worktree

**Preconditions**:
```bash
cd /path/to/worktree-test
# Make some changes
echo "# Test change" >> README.md
git add README.md
git commit -m "test: worktree change"
```

**Action**:
1. Run `python main.py` from worktree directory
2. Select menu `[6] 🧐 Code Review (Local)`

**Expected Output**:
```
🚀 Reviewing TestProject...
   🌿 Worktree detected: Using /path/to/worktree-test instead of /path/to/main/repo
   🔎 Found 1 changed files in TestProject.
   🚀 Running Reviewer on ['README.md']...
   ✅ Review Report saved to: /path/to/worktree-test/code_review.md
```

**Verification**:
```bash
# Check report location
ls -la /path/to/worktree-test/code_review.md
# Expected: File exists

ls -la /path/to/main/repo/code_review.md
# Expected: No such file (or old version if exists)

# Check content
cat /path/to/worktree-test/code_review.md | grep "Test change"
# Expected: Should contain the change made in worktree
```

**Pass Criteria**: ✅ `code_review.md` saved in worktree, contains worktree changes

---

### Step 4: Update Docs from Worktree
**Issue**: #64 - Update Docs อ้างอิง path ผิด

**Preconditions**:
```bash
cd /path/to/worktree-test
# Ensure worktree has different CHANGELOG
echo "## [Unreleased]" > CHANGELOG.md
git add CHANGELOG.md
git commit -m "docs: update changelog in worktree"
```

**Action**:
1. Run `python main.py` from worktree directory
2. Select menu `[7] 📝 Update Docs`
3. Observe output

**Expected Output**:
```
📝 Documentation Update
   Project: TestProject
   🌿 Worktree detected: Using /path/to/worktree-test instead of /path/to/main/repo
⏳ Updating docs (AI-powered)...
   📦 [TestProject] Checking documentation...
   📄 Found: CHANGELOG.md, README.md
```

**Verification**:
```bash
# Check which CHANGELOG was used
grep -r "worktree" /path/to/worktree-test/CHANGELOG.md
# Expected: Contains worktree-specific content

grep -r "worktree" /path/to/main/repo/CHANGELOG.md
# Expected: Does NOT contain worktree-specific content
```

**Pass Criteria**: ✅ Docs read from and written to worktree

---

### Step 5: Update Roadmap from Worktree
**Issue**: #64 - Update Roadmap อ้างอิง path ผิด

**Preconditions**:
```bash
cd /path/to/worktree-test
# Create worktree-specific ROADMAP
mkdir -p docs
cat > docs/ROADMAP.md << 'EOF'
# Worktree Roadmap

## Issue #999
- **Status:** 🟡 In Progress (Worktree)
EOF
git add docs/ROADMAP.md
git commit -m "docs: add worktree roadmap"
```

**Action**:
1. Run `python main.py` from worktree directory
2. Select menu `[U] 🗺️ Update Roadmap`

**Expected Output**:
```
🗺️  Updating Roadmap for TestProject...
   🌿 Worktree detected: Using /path/to/worktree-test instead of /path/to/main/repo
# Should find ROADMAP.md in worktree
```

**Verification**:
```bash
# Check if worktree ROADMAP was found
grep "Worktree Roadmap" /path/to/worktree-test/docs/ROADMAP.md
# Expected: Found

grep "Worktree Roadmap" /path/to/main/repo/docs/ROADMAP.md 2>/dev/null
# Expected: Not found (or different content)
```

**Pass Criteria**: ✅ ROADMAP.md read from worktree

---

### Step 6: Add Issue to Session from Worktree
**Issue**: #64 - Add Issue action ใช้ path ผิด

**Preconditions**:
```bash
cd /path/to/worktree-test
# Already have active issue session
```

**Action**:
1. Run `python main.py` from worktree directory
2. Select menu `[+] ➕ Add Issue (to session)`
3. Select additional issue

**Expected Output**:
```
   🌿 Worktree detected: Using /path/to/worktree-test instead of /path/to/main/repo
✅ Added issue #XXX to current session
🌿 Branch: feat/xxx-existing-branch
```

**Verification**:
```bash
# Verify git operations in worktree
git -C /path/to/worktree-test log --oneline -1
# Expected: Shows recent worktree operations

git -C /path/to/main/repo log --oneline -1
# Expected: Does NOT show worktree operations
```

**Pass Criteria**: ✅ Issue added, git operations in worktree only

---

### Step 7: Regression Test - Main Repo (Non-Worktree)
**Issues**: #64, #70 - ต้องแน่ใจว่าการแก้ไขไม่ทำให้ main repo เสีย

**Preconditions**:
```bash
cd /path/to/main/repo
# Ensure NOT in a worktree
git rev-parse --git-dir
# Should equal git-common-dir (not a worktree)
```

**Action**:
1. Run `python main.py` from main repo directory
2. Test all actions:
   - `[2] 📥 Select Issue` - Create branch, verify in main repo
   - `[6] 🧐 Code Review` - Create code_review.md in main repo
   - `[7] 📝 Update Docs` - Update docs in main repo
   - `[U] 🗺️ Update Roadmap` - Update roadmap in main repo

**Expected**:
- ไม่มีข้อความ "Worktree detected" (เพราะไม่ใช่ worktree)
- ทุก operation ทำงานใน main repo ตามปกติ

**Verification**:
```bash
# No worktree message in output
python main.py 2>&1 | grep -i "worktree"
# Expected: No output (no worktree detection)

# Operations work normally
git branch | grep feat/
# Expected: New branches created in main repo
```

**Pass Criteria**: ✅ Main repo operations work normally, no worktree detection

---

## 🐛 Common Issues & Troubleshooting

### Issue: "Worktree detected" message ไม่แสดง
**Cause**: `resolve_project_target_dir()` ไม่ detect ว่าเป็น worktree
**Fix**: ตรวจสอบว่าอยู่ใน git worktree จริงๆ:
```bash
git rev-parse --git-dir
git rev-parse --git-common-dir
# ถ้าไม่เท่ากัน → เป็น worktree
```

### Issue: Git operations ยังไปที่ main repo
**Cause**: ยังใช้ `project["path"]` แทน `target_dir`
**Fix**: ตรวจสอบว่าแก้ไขครบทุกจุดใน code

### Issue: Test ผ่านแต่ Manual verify ไม่ผ่าน
**Cause**: Test mock `os.getcwd` แต่จริงๆ รันไม่ได้
**Fix**: ตรวจสอบว่ารัน Luma จาก worktree directory จริงๆ

---

## ✅ Sign-off Checklist

- [ ] Step 1: Select Issue สร้าง branch ใน worktree
- [ ] Step 2: Select Issue headless สร้าง branch ใน worktree
- [ ] Step 3: Code Review ตรวจจับ changes ใน worktree
- [ ] Step 4: Update Docs อ่าน/เขียนไฟล์ใน worktree
- [ ] Step 5: Update Roadmap อ่าน/เขียนไฟล์ใน worktree
- [ ] Step 6: Add Issue ทำงานใน worktree
- [ ] Step 7: Main repo (non-worktree) ทำงานปกติ

**Verifier**: _________________ **Date**: _________________ **Signature**: _________________
