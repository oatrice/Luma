# Walkthrough: การเพิ่ม Gemini CLI Connection และ Settings Menu

ตามโจทย์ที่ได้รับเพื่อให้ตั้งค่า **Gemini CLI เป็นค่าเริ่มต้นแทน Gemini API** และสร้าง **Settings Menu** สำหรับสลับการทำงาน ผมได้ดำเนินการตามกระบวนการ Test-Driven Development (TDD) ดังนี้ครับ

## 1. การเพิ่ม Settings Menu (`main.py` & `actions.py`)
ผมได้เพิ่มเมนู **O: ⚙️ Settings** ในหน้าจอหลักของ Luma (`main.py`) ซึ่งกดเข้าใช้งานได้ตลอด 
เมื่อเข้าสู่เมนูดังกล่าว โปรแกรมจะให้เลือก:
1. การเชื่อมต่อ LLM Provider (`gemini` ↔ `openrouter`) 
2. การเชื่อมต่อหลักสำหรับ Agent CLI (`gemini_cli` ↔ `opencode`)

![Settings Menu Preview](https://github.com/oatrice/Luma/assets/settings-menu-placeholder)

การตั้งค่าเหล่านี้จะถูกบันทึกลงในไฟล์ `.luma_global.json` เพื่อให้จดจำค่าระหว่างการเปิดโปรแกรมในครั้งถัดๆ ไป

## 2. การตั้งค่า `config.py` และค่าเริ่มต้น (gemini_cli)
ในไฟล์ `luma_core/config.py` ผมได้เพิ่มลอจิกในการอ่านการตั้งค่าจาก `.luma_global.json` เพื่อใช้เป็นค่าเริ่มต้นในระบบ 
> [!NOTE]
> ฟังก์ชันนี้ได้เขียนเป็น TDD (Red -> Green -> Refactor) โดยเขียนเทสใน `tests/test_config.py` เพื่อบังคับให้ตัวแปล `AGENT_CLI` รับค่าเริ่มต้นเป็น `'gemini_cli'` ตามคำร้องขอครับ (หากไม่มีการปรับเปลี่ยนไว้ใน .luma_global.json)

## 3. เตรียมการเชื่อมต่อไปยัง `gemini cli`
ผมได้สร้างไฟล์และเทสควบคู่กัน:
* `tests/test_gemini_cli.py` : เทสต์ที่เขียนขึ้นมาก่อน โดยคาดหวังว่าเมื่อเรียกใช้ `delegate_task_to_gemini` ระบบจะต้องรันคำสั่ง subprocess `"gemini"` ควบคู่กับ model `gemini-2.5-pro` ตัวเก่งของเรา (ตามที่คุณทดสอบการทนทานไว้ในเอกสารเปรียบเทียบ)
* `luma_core/gemini_cli.py` : ไฟล์ที่เรียกใช้คำสั่งจริง โดยอาศัยตัวแปรและ flag ต่างๆ เหมือนใน `opencode.py`

## 4. ผลลัพธ์จากการ Verification
* การทำงานแบบ TDD ครบถ้วน โดยเทสต์ล่าสุดบน repository จำนวน 62 เทส ผ่านความถูกต้อง 100% (Green status)
* เมนูใช้งานได้จริง และไฟล์ config สามารถดึงค่า Provider ออกมาใช้โดยอิงจาก Global Config ได้แล้วครับ 

## 5. การจัดการกับเอกสารทดสอบ CLI (cli_comparison_results)
ไฟล์สรุปผลที่คุณทดสอบไว้ ได้ถูกย้ายไปเก็บที่ `docs/cli_comparison_results.md` เพื่อง่ายต่อการศึกษาในระดับ repository ของ Luma ครับ
