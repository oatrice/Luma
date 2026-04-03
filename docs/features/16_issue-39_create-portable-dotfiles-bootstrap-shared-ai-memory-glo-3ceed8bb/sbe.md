# SBE: Portable Dotfiles Bootstrap for Shared AI Memory and Global Agents

> Issue: [#39](https://github.com/oatrice/Luma/issues/39)
> Status: Implemented

## Scenario 1: Fresh install creates managed symlinks

**Given** มี template repo อยู่แล้วและ home target ยังไม่มีไฟล์ AI config  
**When** รัน `python3 scripts/install.py --repo-root "$PWD"`  
**Then** ระบบสร้าง symlink ไปยัง:

- `home/.ai-shared-memory.md`
- `home/.codex/AGENTS.md`
- `home/.gemini/GEMINI.md`

### Examples

| Repo Source | Home Target | Expected State |
|---|---|---|
| `home/.ai-shared-memory.md` | `~/.ai-shared-memory.md` | symlink |
| `home/.codex/AGENTS.md` | `~/.codex/AGENTS.md` | symlink |
| `home/.gemini/GEMINI.md` | `~/.gemini/GEMINI.md` | symlink |

## Scenario 2: Copy mode backs up existing regular files

**Given** target file เป็นไฟล์ปกติที่มี content เดิมอยู่แล้ว  
**When** รัน `python3 scripts/install.py --copy --repo-root "$PWD"`  
**Then**

- ไฟล์เดิมถูก backup เป็น `.bak`
- ไฟล์ใหม่ถูก copy มาจาก source
- target ไม่เป็น symlink

### Examples

| Existing Target | Command | Expected Result |
|---|---|---|
| `~/.ai-shared-memory.md` | `install.py --copy` | backup + copied file |
| `~/.codex/AGENTS.md` | `install.py --copy` | backup + copied file |
| `~/.gemini/GEMINI.md` | `install.py --copy` | backup + copied file |

## Scenario 3: Capture syncs machine-local changes back into template repo

**Given** ผู้ใช้แก้ไฟล์ใน home directory เอง  
**When** รัน `python3 scripts/capture.py --repo-root "$PWD"`  
**Then** content ล่าสุดถูก copy กลับเข้า `home/...` ใน template repo

### Examples

| Modified Machine File | Repo Destination | Expected Result |
|---|---|---|
| `~/.ai-shared-memory.md` | `home/.ai-shared-memory.md` | content updated |
| `~/.codex/AGENTS.md` | `home/.codex/AGENTS.md` | content updated |
| `~/.gemini/GEMINI.md` | `home/.gemini/GEMINI.md` | content updated |

## Scenario 4: Vendor files reference shared memory portably

**Given** เปิด vendor-specific agent files ใน template repo  
**Then**

- ต้องพบ `~/.ai-shared-memory.md`
- ต้องไม่พบ absolute path แบบ `/Users/oatrice/...`

### Examples

| File | Must Contain | Must Not Contain |
|---|---|---|
| `home/.codex/AGENTS.md` | `~/.ai-shared-memory.md` | `/Users/oatrice/.ai-shared-memory.md` |
| `home/.gemini/GEMINI.md` | `~/.ai-shared-memory.md` | `/Users/oatrice/.ai-shared-memory.md` |
