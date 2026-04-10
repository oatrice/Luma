# [Issue #4] Zenith Integration with Luma (CLI Wrapper / Headless Mode)

เพื่อให้ **Zenith** สามารถเรียกใช้งาน **Luma** (ใน OpenShell Sandbox หรือบน Host) ผ่าน Subprocess ได้ตามสถาปัตยกรรม Option A โค้ดของฝั่ง Zenith จะต้องถูกปรับปรุงเพื่อให้สื่อสารกับ Luma ผ่าน CLI ได้อย่างสมบูรณ์

## User Review Required

แผนนี้ต้องการให้ทางฝั่งโปรเจกต์ Luma (`/Users/oatrice/Software-projects/Luma`) มีการอัปเดตเพื่อรองรับ Headless Mode เสียก่อน (ดูรายละเอียดใน Open Questions) หากฝั่ง Luma ยังไม่ได้รับการแก้ไข Zenith จะไม่สามารถเรียกใช้ท่านี้ได้จริง

## Proposed Changes

### Zenith Core (`zenith_core`)

เราจะทำการสร้าง Controller หรือ Wrapper ย่อยขึ้นมาเพื่อใช้เรียก `python main.py` ข้ามไปยัง Path ของ Luma

#### [MODIFY] zenith_core/luma.py
- ยกเครื่อง `LumaCLI` ใน `zenith_core/luma.py` ใหม่
- เพิ่มเครื่องมือสำหรับเรียกยิง Subprocess ไปยัง Luma Directory 
- สร้างฟังก์ชันเฉพาะสำหรับเรียกแต่ละ Action เช่น `luma_cli.run_action("code_review")`
- เพิ่มการดักจับ (Parsing) JSON Output (ในกรณีที่ Luma อัปเดตให้คายผลลัพธ์เป็น JSON แล้ว)

#### [MODIFY] agents/coder_agent.py (หากจำเป็น)
- นำ `LumaCLI` (ตัวที่เราสร้างใหม่ด้านบน) เข้ามาประกอบร่างใน `CoderAgent`
- ให้ CoderAgent สามารถเรียก Luma ของจริงช่วยตรวจสอบหรือสร้างแผนให้

## Open Questions

**การทำงานร่วมกับ Luma Repository:**
- แผนนี้คาดหวังว่า Luma จะยอมรับ arguments ลักษณะนี้: `python main.py --action "code_review" --json --project 1`
- คุณอยากให้ฝั่ง Zenith ใช้งาน Luma แบบไหนบ้าง? (เช่น สั่งให้ Luma สร้าง SBE, สั่งให้ Luma รีวิวโค้ด, หรือสั่งให้ Luma อัปเดต State เป็น PREFLIGHT) รบกวนระบุ Use-case หลักเพื่อจะได้กำหนด Interface ของ `luma.py` ให้ครอบคลุมครับ

## Verification Plan

### Automated Tests
- สร้าง Test cases ใน `tests/test_luma_integration.py` ฝั่ง Zenith
- Mock ควบคุมให้ `subprocess.run` ส่งค่ากลับเสมือน Luma ตอบกลับมาเป็น JSON เผื่อกรณีที่เครื่องไม่ได้ติดตั้ง Luma ไว้รันทดสอบ

### Manual Verification
- รันคำสั่งทดสอบจริงจาก Zenith ให้เรียกข้ามกล่องไปยัง Luma และดูว่า Luma ทำงานเปลี่ยน State โปรเจกต์ได้ถูกไหม
