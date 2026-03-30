# 🌐 Language Policy (Global)
- **Chat Responses**: ตอบเป็นภาษาไทยเสมอ (Always respond in Thai).
- **Git Operations**: Git commit messages and Pull Request descriptions MUST be in English only.
- **Internal Documentation**: `task.md`, `implementation_plan.md`, และ `walkthrough.md` ต้องเป็นภาษาไทย (Must be in Thai).
- **Standard Project Documentation**: `README.md`, `CHANGELOG.md`, และ `ROADMAP.md` MUST be in English only.

TDD Mode: Strict Adherence
Goal: Implement features using the Test-Driven Development (TDD) cycle: Red $\rightarrow$ Green $\rightarrow$ Refactor.
1. 🟥 RED: Write the failing test first. Define the required behavior with a minimal test case that currently fails.
2. 🟢 GREEN: Write the simplest production code to make the failing test pass. Write nothing more than required.
3. ✨ REFACTOR: Improve structure, clarity, and remove duplication. Ensure all existing tests remain passing after every change.
Format: Present the solution in three distinct sections: 1. Failing Test, 2. Passing Code, 3. Refactored Code (if any).


## Gemini Added Memories
- เมื่อมีการสร้างไฟล์ code_review.md ในโปรเจกต์ ให้อ่านเนื้อหา (แม้ติด gitignored) สรุปประเด็นสำคัญ ถามเพื่อ clarify และดำเนินการแก้ไขตาม Test suggestions ทั้งหมดโดยใช้กระบวนการ TDD (Red -> Green -> Refactor) เป็นลำดับความสำคัญสูงสุด
- When mocking async Python functions, always use `new_callable=AsyncMock` with `@patch` to prevent silent `TypeError` exceptions inside `try...except` blocks. Also, be aware of Pydantic field aliases; create test data by parsing a dictionary with the aliased key, not by direct keyword argument initialization.
- To resolve mocking errors with singleton instances in Python that have the same name as their module, either rename the instance to avoid the naming collision, or patch the method directly on the class definition (e.g., `@patch.object(MyService, 'my_method')`).

---

## 🔔 Task Completion Notification (Global — Required)

**เมื่อทำงานที่ได้รับมอบหมายเสร็จสิ้น ให้เรียกใช้ tool `notify_task_complete` เป็น action สุดท้ายเสมอ**
ไม่ว่าจะทำงานใน project ใดก็ตาม เว้นแต่ project นั้นจะมี GEMINI.md ของตัวเองที่ระบุไว้ต่างออกไป

- **project**: ชื่อ project ที่กำลังทำงาน (ดูจาก GEMINI.md ของ project หรือชื่อ folder)
- **task**: สรุปสั้นๆ ว่างานคืออะไร
- **status**: `success` | `failure` | `partial` | `retrying` | `limit_reached`
- **duration**: เวลาโดยประมาณ (optional)
- **message**: รายละเอียดเพิ่มเติม (optional)

> ⚙️ Prerequisites: Akasa backend ต้องรันอยู่ที่ `http://localhost:8000`
