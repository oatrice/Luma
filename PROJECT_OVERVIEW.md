# Project Overview: Luma (The Hive) 🧠

**Project Name:** Luma
**Role:** AI Agent Orchestrator & Development Studio
**Vision:** เป็นศูนย์กลาง (Hub) สำหรับสร้าง บริหาร และสั่งงาน AI Agents ให้ทำหน้าที่ตรวจสอบ แก้ไข และเขียนโค้ดสำหรับโปรเจกต์ต่างๆ (เช่น Tetris-Battle) โดยอัตโนมัติ

## 🎯 Key Objectives (วัตถุประสงค์หลัก)
1.  **Agent Orchestration:** ควบคุม Agent หลายตัว (Reviewer, Coder, Architect) ให้ทำงานร่วมกันเป็น Workflow (LangGraph)
2.  **DevOps Automation:** เชื่อมต่อกับ Tools ภายนอก เช่น GitHub (เพื่อดึง Issue/PR), Terminal (เพื่อรัน Test), และ File System
3.  **Context Management:** จัดการ Memory และ Context ข้ามโปรเจกต์ เพื่อให้ Agent เข้าใจงานต่อเนื่อง

## 🛠 Tech Stack
*   **Core:** Python 3.11+
*   **AI Framework:** LangChain, LangGraph (สำหรับ State Management)
*   **LLM Interface:** OpenAI API / Gemini (ผ่าน SDK)
*   **Integration:** GitHub API (PyGithub), Local File System

## 📂 Key Components
*   **`main.py`**: Entry point สำหรับรัน Agent หรือ Workflow หลัก
*   **`github_fetcher.py`**: Module สำหรับดึงข้อมูล Issues, PRs และ Project Board จาก GitHub
*   **`debug_coder.py`**: Specialized Agent สำหรับวิเคราะห์ Error Logs และเสนอวิธีแก้
*   **`.agent/`**: เก็บ Rules, Prompts, และ Workflows ที่ Luma ใช้ยึดถือ

## 🔗 Relationship with Other Projects
*   **Luma** ทำหน้าที่เป็น "Developer" (ผู้สร้าง)
*   **Tetris-Battle** คือ "Product" (ชิ้นงาน) ที่ Luma กำลังพัฒนาและดูแล
