# Goal Description
สรุปสถานะปัจจุบัน: ปัจจุบัน Luma มีการเชื่อมต่อออกไปภายนอกดังนี้ครับ
1. **Gemini API**: ผ่าน `langchain-google-genai` (ใช้โมเดลเช่น `gemini-2.5-pro`)
2. **OpenRouter API**: ผ่าน `langchain-openai` (เรียกใช้โมเดลเช่น `qwen3-coder:free`, `mistral:free`)
3. **GitHub API**: จัดการ Issue, PR, Project board
4. **Opencode CLI**: มีไฟล์รองรับการเรียกผ่าน CLI (`opencode.py`) ถึงแม้จะยังไม่ได้บูรณาการเต็มรูปแบบในวงจรหลัก

เป้าหมายของงานนี้คือ:
1. เพิ่มการเชื่อมต่อ Agentic ไปยัง **Gemini CLI** (`gemini_cli.py`)
2. สร้าง **Settings Menu** เพื่อให้สามารถสลับ **LLM Provider** (Gemini API ↔ OpenRouter API) และ **Agent CLI** (Gemini CLI ↔ Opencode) ได้อย่างอิสระ
3. บันทึกการตั้งค่าเหล่านี้ลงในไฟล์ `.luma_global.json` นอกเหนือจาก `.env` โดยให้ **Gemini CLI เป็นค่าเริ่มต้นแทน Gemini API ในส่วนของการทำงานแบบ Agent**

## User Review Required
> [!NOTE]
> ฟังก์ชัน `agentic_execution` ที่เรียกใช้ `opencode` ปัจจุบันยังถูกจำกัดอยู่ใน `test_opencode.py` แต่การเพิ่ม `gemini_cli` จะเป็นการเตรียมโครงสร้างให้พร้อมใช้งานในลูปหลักของ Luma ครับ

## Proposed Changes

### Configuration
#### [MODIFY] [config.py](file:///Users/oatrice/Software-projects/Luma/luma_core/config.py)
- ปรับให้อ่านค่า `LLM_PROVIDER` และ `AGENT_CLI` จากไฟล์ `.luma_global.json` หากมีการตั้งค่าไว้ มิฉะนั้นให้ใช้ค่าเริ่มต้น (gemini)

### Integration
#### [NEW] [gemini_cli.py](file:///Users/oatrice/Software-projects/Luma/luma_core/gemini_cli.py)
- สร้างฟังก์ชัน `delegate_task_to_gemini(task_file_path, project_path)` ที่ใช้ `subprocess.run(['gemini', ...])`

#### [NEW] [test_gemini_cli.py](file:///Users/oatrice/Software-projects/Luma/tests/test_gemini_cli.py)
- สร้าง Test File สำหรับทดสอบ `gemini_cli.py` ตามหลัก TDD

### UI & Actions
#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/Luma/main.py)
- เพิ่มเมนู `O` (Settings) เข้าไปใน `MENU_ACTIONS` เปิดให้กดเข้าตั้งค่าได้ทุก Phase

#### [MODIFY] [actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions.py)
- เพิ่มฟังก์ชัน `action_settings()` ที่หน้าจอจะให้เลือกสลับ Provider ระหว่าง (Gemini API / OpenRouter API) และ CLI Agent (Opencode / Gemini CLI)
- เพิ่มตรรกะในการบันทึก / อัปเดตไฟล์ `.luma_global.json`

## Verification Plan
ตามที่ระบุในคำสั่ง (TDD: Red -> Green -> Refactor):
### Automated Tests
1. **เขียน Failed Test (RED):** ใน `tests/test_gemini_cli.py` ให้เรียก `delegate_task_to_gemini` และตรวจสอบ mock subprocess. `pytest tests/test_gemini_cli.py` (จะพังเพราะยังไม่มีไฟล์จริง)
2. **เขียน Passing Code (GREEN):** สร้างไฟล์ `gemini_cli.py` ใส่ฟังก์ชันเปล่าๆ และทำให้เทสผ่าน
3. ตรวจสอบ Configuration (Unit Test สำหรับ `config.py` ว่าอ่านจาก `.luma_global.json` ถูกต้อง)

### Manual Verification
1. สั่งรัน `luma` ไปที่หน้าเมนูหลัก ตรวจสอบว่ามีปุ่มกดเลือกเมนู `⚙️ Settings`
2. ทดสอบกดเข้า Settings และสลับค่า LLM Provider เป็น OpenRouter และ Agent CLI เป็น Gemini CLI
3. ปิดแล้วเปิดโปรแกรมใหม่เพื่อดูว่าค่าที่สลับถูกจดจำไว้ใน `.luma_global.json` หรือไม่
