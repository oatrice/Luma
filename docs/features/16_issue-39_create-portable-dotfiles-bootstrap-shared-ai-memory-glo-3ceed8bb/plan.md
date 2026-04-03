# Implementation Plan: Portable Dotfiles Bootstrap for Shared AI Memory and Global Agents

> Status: Implemented
> Issue: [#39](https://github.com/oatrice/Luma/issues/39)

## 1. Plan Overview

implementation จริงของ issue นี้ถูกทำในรูปแบบ “template repo inside Luma” ไม่ใช่ external repository โดยตรง

root หลักของงานคือ [docs/templates/dotfiles-repo](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo)

## 2. Implementation Steps

### Step 1: Create portable dotfiles template structure

เพิ่มไฟล์พื้นฐานของ template repo:

- `README.md`
- `AGENTS.md`
- `.gitignore`
- `manifest.json`
- `home/.ai-shared-memory.md`
- `home/.codex/AGENTS.md`
- `home/.gemini/GEMINI.md`

เหตุผล:

- ให้มี template ที่ครบพอสำหรับ extract ไปเป็น repo จริงบนเครื่องใหม่
- ให้ vendor-specific files ถูกเก็บคู่กับ shared memory ในที่เดียว

### Step 2: Centralize source/target mapping

เพิ่ม [manifest.json](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/manifest.json) เพื่อเก็บ mapping ระหว่าง:

- source path ใน repo
- target path ใน home directory

และเพิ่ม [scripts/_shared.py](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/scripts/_shared.py) เพื่อ reuse logic อ่าน manifest และจัดการ backup

### Step 3: Implement installer

เพิ่ม [scripts/install.py](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/scripts/install.py)

behavior:

- default เป็น symlink install
- รองรับ `--copy`
- ถ้า target เดิม conflict กับ source ปัจจุบัน ให้ backup ก่อน
- ถ้า target เป็น managed link เดิมอยู่แล้ว ให้ตอบ `unchanged`

### Step 4: Implement capture flow

เพิ่ม [scripts/capture.py](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/scripts/capture.py)

behavior:

- อ่าน mapping จาก manifest เดียวกัน
- copy ไฟล์จาก home directory กลับเข้ามาใน `home/...` ของ template repo
- ข้ามไฟล์ที่เป็น managed link เดิมอยู่แล้ว

### Step 5: Seed global memory and vendor rules

เติม content เริ่มต้นให้:

- [home/.ai-shared-memory.md](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/home/.ai-shared-memory.md)
- [home/.codex/AGENTS.md](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/home/.codex/AGENTS.md)
- [home/.gemini/GEMINI.md](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/home/.gemini/GEMINI.md)

เกณฑ์สำคัญ:

- shared memory ต้องเป็น source of truth ร่วม
- vendor files ต้องอ้าง shared memory แบบ portable ผ่าน `~/.ai-shared-memory.md`

### Step 6: Add regression tests

เพิ่ม [tests/test_dotfiles_repo_template.py](/Users/oatrice/Software-projects/Luma/tests/test_dotfiles_repo_template.py)

tests ที่ครอบ:

- template structure ครบ
- portable references ครบ
- install script สร้าง symlink ได้
- capture script sync กลับเข้า repo ได้

## 3. Verification Plan

### Automated

```bash
python3 -m pytest -q tests/test_dotfiles_repo_template.py
./venv/bin/python -m ruff check tests/test_dotfiles_repo_template.py docs/templates/dotfiles-repo/scripts/_shared.py docs/templates/dotfiles-repo/scripts/install.py docs/templates/dotfiles-repo/scripts/capture.py --ignore E501,F401
PYTHONPYCACHEPREFIX=/tmp/luma-dotfiles-pycache python3 -m py_compile tests/test_dotfiles_repo_template.py docs/templates/dotfiles-repo/scripts/_shared.py docs/templates/dotfiles-repo/scripts/install.py docs/templates/dotfiles-repo/scripts/capture.py
```

### Manual

1. copy template ไปยัง temp directory
2. รัน `install.py` แบบ default แล้วตรวจว่าได้ symlink
3. แทนที่ target ด้วยไฟล์ปกติ แล้วรัน `install.py --copy`
4. ตรวจว่าได้ `.bak` และ content ใหม่ตรงกับ source
5. แก้ไฟล์ใน home target แล้วรัน `capture.py`
6. ตรวจว่า content ถูก sync กลับเข้า repo template

## 4. Follow-up Work

เรื่องต่อไปที่ไม่อยู่ใน scope ของ PR นี้:

- [#40](https://github.com/oatrice/Luma/issues/40) headless Select Issue
- [#41](https://github.com/oatrice/Luma/issues/41) machine-readable guided workflow
- [#42](https://github.com/oatrice/Luma/issues/42) first-class issue creation
- [#43](https://github.com/oatrice/Luma/issues/43) Telegram step-progress updates
- [#44](https://github.com/oatrice/Luma/issues/44) doc-quality validation
