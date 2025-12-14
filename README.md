# 🧠 Luma (The Hive)

**Luma** is a Multi-Agent System (MAS) designed to serve as an "AI Software Architect" for the **Tetris-Battle** project. It acts as an automated software development team that writes code, ensures quality, and manages GitHub Workflows autonomously.

## 🏗️ Architecture

Luma is built using **LangGraph** and is composed of several specialized agents:

- **🤖 Coder**: A polyglot expert (Python, Go, C++) responsible for writing code based on requirements and fixing bugs.
- **🧐 Reviewer**: Analyzes code quality, identifies logic errors, and ensures memory safety (specifically for C++/Go).
- **🧪 Tester**: Runs Unit Tests (or Build Tests) to verify that the generated code functions correctly.
- **✋ Approver**: (Human-in-the-loop) Awaits user approval before persisting files or pushing changes to Git.
- **💾 Writer**: Handles file system operations to save code to the target project (Tetris-Battle).
- **🚀 Publisher**: Automates Git operations—creating branches, committing changes, and opening Pull Requests (PR) on GitHub.

## 🛠️ Tech Stack

- **Core**: Python 3.11+
- **Framework**: LangChain, LangGraph
- **LLM Providers**: Google Gemini (Default), OpenRouter (Optional)

## 📦 Installation & Setup

1. **Clone Repository**
   ```bash
   git clone <repository_url>
   cd Luma
   ```

2. **Setup Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file from `.env.example` and add your API Keys:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` with your credentials:*
   ```ini
   GOOGLE_API_KEY=your_gemini_api_key
   # OR
   OPENROUTER_API_KEY=your_openrouter_key
   
   # For GitHub Integration
   GITHUB_TOKEN=your_personal_access_token
   ```

## 🚀 Usage

### 1. Manual Task Mode
Run Luma to solve the default task defined in `main.py` or to test the system manually.
```bash
python main.py
```

### 2. GitHub Issue Driven Mode
Connect Luma to a GitHub Project to fetch issues, act on them (Update Status -> Write Code -> Create PR).
```bash
python main.py --github --repo oatrice/Tetris-Battle
```
(You can change `--repo` to your target repository).

## 🧪 Workflow Loop (TDD)
Luma operates in an iterative loop:
1. **Plan & Code**: Analyzes the task and writes the implementation.
2. **Review**: Static analysis and code review.
3. **Test**: Executes tests.
   - ❌ If **Fail**: Sends feedback back to the **Coder** for fixing (Retries up to 3 times).
   - ✅ If **Pass**: Forwards to the **Approver**.
4. **Deploy**: Upon user approval -> Saves Files -> Creates PR.
