# 🧪 Luma Manual Test Checklist & Regression Scripts

Use this checklist to verify each phase of the Luma Workflow Guardian using `python3 main.py` and automated tests.

## 🔄 Regression Test (All Phases)
Run this command to verify all logic at once:
```bash
PYTHONPATH=. pytest tests/
```
- [ ] All tests passed (Green)

---

## 🛠 Phase-by-Phase Manual Verification

### Phase 1: State Management
**Goal**: Verify state persists across sessions.
- [ ] **Step 1**: Run `python3 main.py`.
- [ ] **Step 2**: Select `Start Task` -> Enter task name "Test Phase 1".
- [ ] **Step 3**: Verify UI shows "Coding" status (Green header).
- [ ] **Step 4**: Exit (Ctrl+C).
- [ ] **Step 5**: Run `python3 main.py` again.
- [ ] **Step 6**: Verify Luma remembers "Test Phase 1" is in progress (Auto-resume).
- [ ] **Step 7**: Select `Finish Task`. Verify status returns to "Idle".

### Phase 2: GitHub Integration
**Goal**: Verify Kanban board synchronization.
- [ ] **Step 1**: Ensure `GH_TOKEN` is set.
- [ ] **Step 2**: Run `python3 main.py`.
- [ ] **Step 3**: Choose `Select Issue from Kanban`.
- [ ] **Step 4**: Pick an issue from the list (e.g., "Implement X").
- [ ] **Step 5**: Go to GitHub Project Board in browser.
- [ ] **Step 6**: Verify the chosen issue moved to **In Progress** column.

### Phase 3: Pre-flight Checker
**Goal**: Verify rules block invalid actions.
- [ ] **Step 1**: In `JarWise/.luma_rules.json`, add a dummy check:
  ```json
  {
    "id": "must_fail",
    "type": "file_exists",
    "path": "NON_EXISTENT_FILE.txt",
    "required": true
  }
  ```
- [ ] **Step 2**: Run `python3 main.py` in `JarWise` directory.
- [ ] **Step 3**: Try to `Submit PR`.
- [ ] **Step 4**: Verify Luma **Blocks** the action and shows "Missing file: NON_EXISTENT_FILE.txt".
- [ ] **Step 5**: Remove the dummy rule to restore state.

### Phase 4: Context Summarizer
**Goal**: Verify context specific to project is shown.
- [ ] **Step 1**: Run `python3 main.py` in `JarWise/Android`.
- [ ] **Step 2**: Verify the dashboard/menu shows an "Android Context" section (or similar).
- [ ] **Step 3**: Verify it lists "Follow Material Design 3" (from `.luma_rules.json`).

### Phase 5: UI Upgrade
**Goal**: Visual Check.
- [ ] **Step 1**: Run `python3 main.py`.
- [ ] **Step 2**: Check Header:
  - **Idle**: Blue background 🔵
  - **Coding**: Green background 🟢
  - **PR Pending**: Orange/Yellow background 🟠
- [ ] **Step 3**: Check "Next Step" suggestion helps guide the flow.

### Phase 6: Project Configuration (New)
**Goal**: Verify loading of new JSON configs.
- [ ] **Step 1**: Run the verification script:
  ```bash
  PYTHONPATH=. python3 tests/verify_phase6.py
  ```
- [ ] **Step 2**: Verify output shows "Rules loaded successfully" and "Validation passed".

---

## 🚀 End-to-End User Journey (Full Manual Regression)
**Scenario**: A developer starts working on a new feature, verifies it, and submits a PR.

### 1. Start & Context
- [ ] Open Terminal in `JarWise/Android` (Project with rules).
- [ ] Run `python3 ../../Luma/main.py` (simulate running from project root).
- [ ] **Check**: Header is BLUE (Idle) with correct emoji.
- [ ] **Check**: "Context" section displays Android-specific rules (Phase 4 & 6).

### 2. Issue Selection & State Transition
- [ ] Select `Select Issue from Kanban` (Phase 2).
- [ ] Pick an issue (e.g., "Fix Login Bug").
- [ ] **Check**: Terminal clears. Header turns GREEN (Coding) (Phase 1 & 5).
- [ ] **Check**: Active Task displays "Fix Login Bug".
- [ ] (Verification) Check GitHub Board: Issue moved to **In Progress**.

### 3. Work Simulation & Persistence
- [ ] Press `Ctrl+C` to exit Luma.
- [ ] Run `python3 ../../Luma/main.py` again.
- [ ] **Check**: Auto-resumes in GREEN (Coding) state with "Fix Login Bug" (Phase 1).

### 4. Pre-flight & Rules Implementation
- [ ] Select `Create Pull Request`.
- [ ] **Check**: Shows "Running Pre-flight Checks..." (Phase 3).
- [ ] **Check**: Fails if `CHANGELOG.md` is not modified (Rule: `file_modified`) (Phase 6).
- [ ] **Action**: Modify `CHANGELOG.md` (add a dummy line).
- [ ] Select `Create Pull Request` again.
- [ ] **Check**: Pre-flight passes 🟢.

### 5. Completion & Sync
- [ ] (Mocked PR Creation flow) Luma asks for PR details.
- [ ] Completes PR creation.
- [ ] **Check**: State moves to ORANGE (PR Pending) or back to BLUE (Idle).
- [ ] (Verification) Check GitHub Board: Issue moved to **In Review** (Phase 2).
