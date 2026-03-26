# Luma CLI Enhancements: Roadmap & GitHub Issues Sync

## Goal Description
Enhance Luma CLI to automate GitHub issue management, keep `Roadmap.md` in sync, and refactor long methods in `actions.py`.

## Proposed Changes

### 1. Refactor `actions.py` (L1880-L2050)
- **Problem:** `action_update_docs` and `action_refine_issue` are getting too long and hard to maintain.
- **Solution:** Extract logic into modular private functions:
  - `_get_target_repos_for_docs()`: Handle repo selection logic.
  - `_execute_docs_update_and_summarize()`: Handle the update loop and print the summary (around lines 1980-2010).
  - `_prepare_analyst_state()`: Handle the setup logic for the analyst agent.

### 2. Feature: GitHub Issues <-> Roadmap Sync
- **The Pain Point:** "จากสร้าง issue ใหม่แล้ว Roadmap ไม่อัพตาม" (When creating a new issue, Roadmap gets out of sync).
- **Solution:** 
  1. **Create Issue via Luma:** Provide a way to create an Issue directly from Luma using `gh issue create`. เมื่อสร้างเสร็จ Luma จะวิ่งไปอัพเดทไฟล์ `Roadmap.md` ให้อัตโนมัติ.
  2. **Auto-Sync at Update Roadmap step:** เมื่อ Luma ทำงานถึงขั้นตอน `✅ Done.` แล้วถามว่า `Update Roadmap? (Y/n):` จะเพิ่มตรรกะให้ไปเช็ค Issue ล่าสุดบน GitHub ถ้ามี Issue ใหม่ที่ยังไม่มีใน `Roadmap.md` ให้ดึงมาเติมท้าย `Roadmap.md` อัตโนมัติ.

### 3. Feature: Smart Issue Selection Recommendation
- **The Request:** ตอนที่เข้าเมนู `[2] 📥 Select Issue` ให้เช็ค `gh cli` และ `Roadmap.md` ว่าควรทำ issue ไหนต่อ.
- **Solution:** ก่อน Fetching Kanban เราจะใช้ LLM หรือ Logic ง่ายๆ อ่าน `Roadmap.md` เทียบกับ Issue ที่เปิดอยู่ แล้ว Print คำแนะนำ (Recommendation) ขึ้นมาบอกผู้ใช้ว่า "💡 ถัดไปควรทำ Issue #... เพราะ..."

## User Review Required
> [!IMPORTANT]
> - การปรับปรุงเรื่อง Code Modularity (แยกฟังก์ชันให้สั้นลง) แบบที่อธิบายด้านบน ตรงกับที่ต้องการใช่ไหมครับ?
> - ตอนเช็ค `Roadmap.md` เพื่อแนะนำว่าควรทำ issue ไหนต่อ ต้องการให้ใช้ AI (`luma_core.llm`) วิเคราะห์เนื้อหาเลยไหมครับ หรือแค่ดึงบรรทัดแรกที่ status ทิ้งไว้มาแสดง?
> - สำหรับการสร้าง issue ใหม่ ต้องการให้มีเมนูแยก `[+] Create New Issue to GitHub` ขึ้นมาในหน้าแรกเลยไหมครับ หรือรวมอยู่ในเมนูไหนเป็นพิเศษไหมครับ?

## Verification Plan
### Automated Tests
- Mock `subprocess.run` สำหรับฟังก์ชัน `create_issue_via_gh` และการเรียกเช็ค issue ผ่าน `gh`.
- ตรวจสอบ Unit Test ให้ครอบคลุมฟังก์ชันที่เรา refactor ออกมา (`_get_target_repos_for_docs` etc.).

### Manual Verification
- รัน Luma CLI ตรวจสอบ Output ใน console ระหว่าง Update Docs และ Update Roadmap ว่ายังทำงานเหมือนเดิม.
- ทดสอบ "Create Issue", และดูว่า `Roadmap.md` รับรู้ Issue ใหม่หรือไม่.
