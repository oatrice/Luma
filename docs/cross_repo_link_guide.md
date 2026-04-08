# Cross-Repo Link Guide
## เชื่อมโยง Issues ข้าม Repository (Luma ↔ Zenith)

### Overview

Feature นี้ช่วยให้สามารถสร้างความเชื่อมโยง (link) ระหว่าง issues ที่อยู่คนละ repository ได้โดยอัตโนมัติ

### Supported Repositories
- **Luma** → **Zenith** (auto-detect)
- **Zenith** → **Luma** (via GitHub Action)
- Any repo → Any repo (manual mode)

---

## วิธีใช้งาน

### 1. Interactive Mode (Menu N)

```bash
# Run Luma normally
python main.py

# Select [N] Create New Issue
🆕 Create New Issue
```

**Auto-detect จะทำงานเมื่อ:**
- ใส่ Zenith URL ใน body (e.g., `https://github.com/oatrice/Zenith/issues/19`)
- ใส่ Zenith reference (e.g., `Zenith#19`, `oatrice/Zenith#19`)
- ชื่อ branch มี pattern `zenith-19-description`

**หลังจาก create issue:**
- Luma จะ post backlink comment ไปยัง Zenith issue อัตโนมัติ
- Zenith issue จะมี comment แสดงว่าถูกอ้างอิงโดย Luma issue ใด

### 2. Headless Mode

```bash
# Create issue with manual cross-repo links
python main.py --headless --action create_issue \
  --issue-title "Feature X for Zenith#19" \
  --issue-body "Implement feature for Zenith integration" \
  --related oatrice/Zenith#19 oatrice/Zenith#22
```

**Parameters:**
- `--issue-title`: หัวข้อ issue
- `--issue-body`: เนื้อหา issue (รองรับ Markdown)
- `--issue-labels`: Labels เช่น `enhancement`, `bug`
- `--related`: Cross-repo links (หลายอันได้)

### 3. Issue Selection (Auto-detect)

เมื่อเลือก issue จาก Kanban ([2] Select Issue):

```bash
# Select [2] Select Issue (from Kanban)
```

Luma จะ:
1. Auto-detect Zenith issues จาก issue body ที่เลือก
2. แสดง notification ถ้าพบ cross-repo links
3. เก็บ links ไว้ใน state สำหรับใช้ตอน create PR

**Example output:**
```
🔗 Cross-Repo Links Detected (2):
   • oatrice/Zenith#19 → https://github.com/oatrice/Zenith/issues/19
   • oatrice/Zenith#22 → https://github.com/oatrice/Zenith/issues/22
   💡 Links will be auto-included when creating PR
```

### 4. PR Creation (Auto-link)

เมื่อสร้าง PR ใน Luma ที่อ้างอิงถึง Zenith issues:

```bash
# Select [P] Create/Sync PRs หรือ [8] Create Pull Request
```

Luma จะ:
1. Auto-detect Zenith issues จาก issue body
2. Auto-detect จากชื่อ branch
3. ใช้ cross-repo links ที่เก็บไว้ตอน select issue (ถ้ามี)
4. Append `## 🔗 Cross-Repo Links` section ใน PR description
5. Post backlink comment ไปยัง Zenith issues

**Example PR Description:**
```markdown
## Summary
Implement feature X

Closes #42

## 🔗 Cross-Repo Links
- Related: [oatrice/Zenith#19](https://github.com/oatrice/Zenith/issues/19)
- Related: [oatrice/Zenith#22](https://github.com/oatrice/Zenith/issues/22)
```

---

## Workflow Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  1. Select      │────▶│  2. Work/Commit  │────▶│  3. Create PR   │
│     Issue       │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
        ▼                       │                        ▼
┌──────────────┐               │              ┌─────────────────┐
│ Auto-detect  │               │              │  Include links  │
│ Zenith refs  │───────────────┼─────────────▶│  from state +   │
│ from body    │               │              │  fresh detect   │
└──────────────┘               │              └─────────────────┘
        │                      │                        │
        ▼                      │                        ▼
┌──────────────┐               │              ┌─────────────────┐
│ Store in     │               │              │ Post backlink   │
│ state.context│               │              │ to Zenith       │
└──────────────┘               │              └─────────────────┘
```

---

## Auto-Detect Patterns

### จาก Issue Body
- `oatrice/Zenith#19`
- `Zenith#19`
- `https://github.com/oatrice/Zenith/issues/19`

### จาก Branch Name
- `feature/zenith-19-description`
- `fix-zenith-22-bug`
- `zenith/19-description`

---

## โครงสร้าง Files

```
Luma/
├── luma_core/
│   └── actions/
│       ├── create_issue_action.py    # Main implementation
│       ├── workflow_actions.py        # PR integration
│       └── __init__.py                # Exports
├── main.py                            # CLI integration
└── docs/
    └── cross_repo_link_guide.md       # This file

Zenith/
└── .github/
    └── workflows/
        └── cross-repo-link-notifier.yml  # GitHub Action
```

---

## Testing

### Test Auto-detect
```python
from luma_core.actions import detect_zenith_issues_from_text

links = detect_zenith_issues_from_text(
    "This relates to Zenith#19 and oatrice/Zenith#22"
)
print(f"Detected {len(links)} Zenith issues")
```

### Test Branch Detection
```python
from luma_core.actions import detect_zenith_issues_from_branch

links = detect_zenith_issues_from_branch("feature/zenith-25-new-ui")
print(f"Detected {len(links)} issues from branch")
```

---

## Troubleshooting

### Backlink not posted
- เช็คว่า Zenith repo มี GitHub Action อยู่
- เช็ค Personal Access Token มี permission `issues:write`

### Auto-detect not working
- ตรวจสอบ pattern (case-sensitive สำหรับ URL)
- ลองใช้ manual `--related` flag

### Cross-repo link in PR not showing
- เช็คว่า issue body มี Zenith reference
- ลอง push branch ใหม่ที่มี pattern `zenith-N`

---

## Future Enhancements

- [ ] Support bi-directional sync (Zenith → Luma)
- [ ] Auto-create issues in Zenith when Luma issue mentions Zenith feature
- [ ] Dashboard แสดง cross-repo link graph
