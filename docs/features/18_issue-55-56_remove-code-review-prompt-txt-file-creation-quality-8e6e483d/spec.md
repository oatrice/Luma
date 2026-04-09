# Specification: Remove code_review_prompt.txt & Fix worktree path resolution

> **Status**: Proposed
> **Owner**: Gemini CLI
> **Dates**: Created: 2026-04-09 | Last Updated: 2026-04-09

## 1. Context & Goal
*ทำไมเราถึงสร้างสิ่งนี้? ปัญหาคืออะไร?*

### Problem
1. **ไฟล์ขยะ (Workspace Clutter)**: ในไฟล์ `quality_actions.py` มีการสร้างไฟล์ `code_review_prompt.txt` ทิ้งไว้ใน workspace ทุกครั้งที่มีการรันกระบวนการ Code Review ซึ่งเป็นไฟล์ชั่วคราวที่ไม่จำเป็นต้องเขียนลงดิสก์ ทำให้เกิดความรกในโครงการ
2. **การระบุ Path ใน Worktree ผิดพลาด**: เมื่อใช้งาน Luma จาก Git Worktree (เช่น `Cerebro-worktrees/feat-x`) ตัว Luma กลับไปเขียนไฟล์ output (เช่น `code_review.md`) ลงใน Repository หลัก (Main Repo) แทนที่จะเขียนลงใน Worktree ที่กำลังทำงานอยู่ เนื่องจากระบบดึง path จาก config โดยตรงโดยไม่ได้ตรวจสอบว่ากำลังรันอยู่ใน Worktree หรือไม่

### Goal
1. ยกเลิกการสร้างไฟล์ `code_review_prompt.txt` แบบอัตโนมัติ
2. ปรับปรุงระบบ Path Resolution ให้รองรับ Git Worktree อย่างถูกต้อง เพื่อให้ไฟล์ output ถูกบันทึกไปยังตำแหน่งที่ผู้ใช้กำลังทำงานจริง

---

## 2. User Journey & Requirements
*ประสบการณ์ที่ผู้ใช้ควรได้รับคืออะไร?*

### User Story
As a **Developer using Git Worktrees**, I want **Luma to save output files into my current worktree and keep the workspace clean**, so that **my changes are isolated to the correct environment and I don't have unnecessary temporary files**.

### Functional Requirements
- [ ] ระบบต้องไม่สร้างไฟล์ `code_review_prompt.txt` ลงใน directory ของโปรเจกต์เป้าหมาย
- [ ] เมื่อรัน Luma ใน Git Worktree, ระบบต้องตรวจพบ (detect) actual path ของ worktree นั้น
- [ ] ไฟล์ output ทั้งหมด (เช่น `code_review.md`) ต้องถูกเขียนลงใน root directory ของ worktree ที่กำลังใช้งานอยู่
- [ ] การทำงานใน Repository ปกติ (Non-worktree) ต้องยังคงทำงานได้ถูกต้องเหมือนเดิม

### Non-Functional Requirements
- **Reliability**: การจัดการ Path ต้องแม่นยำ ไม่ทำให้ไฟล์ไปโผล่ในที่ที่ไม่ควรอยู่
- **Maintainability**: ใช้ฟังก์ชันกลางในการ resolve path เพื่อให้ง่ายต่อการแก้ไขในอนาคต

---

## 3. Specification by Example (SBE)
*ตัวอย่างพฤติกรรมที่เป็นรูปธรรม*

### Scenario: การกำจัดไฟล์ชั่วคราว (Clutter Reduction)
**Given** ผู้ใช้รันคำสั่ง Code Review ในโปรเจกต์ใดๆ
**When** กระบวนการสร้างคำแนะนำ (Draft Review) เสร็จสิ้น
**Then** จะต้องไม่มีไฟล์ชื่อ `code_review_prompt.txt` ปรากฏอยู่ในโฟลเดอร์ของโปรเจกต์

#### Examples
| Action | File `code_review_prompt.txt` | Result |
|-------|-----------------------------|--------|
| Run Code Review | ไม่ถูกสร้าง | Pass |
| Run Code Review | ถูกลบออก (ถ้าเคยมี) | Pass |

### Scenario: การบันทึกไฟล์ใน Git Worktree
**Given** โปรเจกต์ `Cerebro` ถูกตั้งค่าไว้ที่ `~/Projects/Cerebro` และผู้ใช้กำลังทำงานอยู่ที่ worktree `~/Projects/Cerebro-worktrees/feat-fix-bug`
**When** ผู้ใช้รัน Luma ผ่านคำสั่ง `python3 path/to/Luma/main.py` จากใน worktree
**Then** ไฟล์ `code_review.md` ต้องถูกบันทึกไว้ที่ `~/Projects/Cerebro-worktrees/feat-fix-bug/code_review.md`

#### Examples
| Current Directory (PWD) | Config Project Path | Expected Output Path |
|-------|--------|-------|
| `~/Cerebro` | `~/Cerebro` | `~/Cerebro/code_review.md` |
| `~/Cerebro-worktrees/feat-A` | `~/Cerebro` | `~/Cerebro-worktrees/feat-A/code_review.md` |
| `~/Cerebro-worktrees/fix-B` | `~/Cerebro` | `~/Cerebro-worktrees/fix-B/code_review.md` |

---

## 4. Constraints & Risks
*สิ่งที่ต้องระวัง*
- **Path Resolution**: ต้องมั่นใจว่า `resolve_project_target_dir()` ทำงานได้ถูกต้องในทุก OS (Darwin/Linux)
- **Git Context**: หากรัน Luma จากนอก Git repository หรือในโฟลเดอร์ที่ไม่เกี่ยวข้องกับโปรเจกต์ใน config ระบบควรมี fallback ที่เหมาะสม (เช่น กลับไปใช้ path จาก config)
- **Compatibility**: การแก้ไขใน `luma_core/tools.py` อาจส่งผลกระทบต่อ Action อื่นๆ ที่เรียกใช้ฟังก์ชันเดียวกัน จึงต้องมีการทำ Regression Test อย่างละเอียด