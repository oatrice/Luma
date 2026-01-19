"""
Pre-Coding Status Checker

ตรวจสอบและเตือนลำดับขั้นตอนก่อนเริ่มเขียน Code
"""

import os
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Pre-Coding Phases
PHASES = {
    1: {"name": "Analysis", "emoji": "🔍", "description": "วิเคราะห์ปัญหาและความต้องการ"},
    2: {"name": "Design", "emoji": "📐", "description": "ออกแบบระบบและ UI/UX"},
    3: {"name": "Planning", "emoji": "📋", "description": "ย่อยงานและประเมินเวลา"},
    4: {"name": "Coding", "emoji": "💻", "description": "เขียน Code"},
}

# Analysis checklist items
ANALYSIS_CHECKS = [
    ("requirement_analysis", "Requirement Analysis", "ระบุ User Stories และ Acceptance Criteria"),
    ("feature_analysis", "Feature Analysis", "วิเคราะห์ฟังก์ชันและ User Flow"),
    ("impact_analysis", "Impact Analysis", "วิเคราะห์ผลกระทบต่อระบบเดิม"),
    ("feasibility_analysis", "Feasibility Analysis", "ประเมินความเป็นไปได้"),
    ("security_analysis", "Security Analysis", "วิเคราะห์ความปลอดภัย"),
    ("performance_analysis", "Performance Analysis", "วิเคราะห์ Performance"),
    ("risk_analysis", "Risk Analysis", "วิเคราะห์ความเสี่ยง"),
]

# Design checklist items
DESIGN_CHECKS = [
    ("database_schema", "Database Schema", "ออกแบบ ER Diagram และ Tables"),
    ("system_architecture", "System Architecture", "วาด System Diagram"),
    ("api_spec", "API Specification", "กำหนด Endpoints และ Schemas"),
    ("ui_ux_design", "UI/UX Design", "สร้าง Wireframes/Mockups"),
]

# Planning checklist items
PLANNING_CHECKS = [
    ("task_breakdown", "Task Breakdown", "ย่อยงานเป็น Tasks ย่อย"),
    ("estimation", "Estimation", "ประเมินเวลาแต่ละ Task"),
    ("definition_of_done", "Definition of Done", "กำหนดเกณฑ์ DoD"),
]


def check_feature_docs(project_path: str) -> Dict:
    """
    Check for feature documentation files in docs/features/
    Returns dict with found docs and their status
    """
    docs_path = os.path.join(project_path, "docs", "features")
    results = {
        "found": False,
        "files": [],
        "latest": None,
        "has_analysis": False,
        "has_design": False,
        "has_planning": False,
    }
    
    if not os.path.exists(docs_path):
        return results
    
    # Find all feature docs
    pattern = os.path.join(docs_path, "*.md")
    files = glob.glob(pattern)
    
    if files:
        results["found"] = True
        for f in files:
            basename = os.path.basename(f)
            mtime = os.path.getmtime(f)
            results["files"].append({
                "name": basename,
                "path": f,
                "mtime": mtime
            })
        
        # Sort by modification time (newest first)
        results["files"].sort(key=lambda x: x["mtime"], reverse=True)
        results["latest"] = results["files"][0] if results["files"] else None
        
        # Check content of latest file for sections
        if results["latest"]:
            try:
                with open(results["latest"]["path"], "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    
                    # Check for analysis markers
                    analysis_markers = ["requirement", "impact", "feasibility", "security", "risk"]
                    results["has_analysis"] = any(m in content for m in analysis_markers)
                    
                    # Check for design markers
                    design_markers = ["database", "schema", "architecture", "api", "wireframe", "ui/ux"]
                    results["has_design"] = any(m in content for m in design_markers)
                    
                    # Check for planning markers  
                    planning_markers = ["task", "estimation", "breakdown", "definition of done", "dod"]
                    results["has_planning"] = any(m in content for m in planning_markers)
            except:
                pass
    
    return results


def check_git_status(project_path: str) -> Dict:
    """
    Check git status for the project
    """
    import subprocess
    
    results = {
        "current_branch": None,
        "is_feature_branch": False,
        "has_uncommitted": False,
        "commits_ahead": 0,
    }
    
    try:
        # Get current branch
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        branch = res.stdout.strip()
        results["current_branch"] = branch
        results["is_feature_branch"] = branch not in ["main", "master", ""]
        
        # Check for uncommitted changes
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        results["has_uncommitted"] = len(res.stdout.strip()) > 0
        
        # Count commits ahead of main
        if results["is_feature_branch"]:
            res = subprocess.run(
                ["git", "rev-list", "--count", f"origin/main..{branch}"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            try:
                results["commits_ahead"] = int(res.stdout.strip())
            except:
                pass
                
    except Exception as e:
        results["error"] = str(e)
    
    return results


def check_issue_status(project_path: str, repo_slug: str) -> Dict:
    """
    Check for active/in-progress issues
    """
    results = {
        "has_active_issue": False,
        "issue_number": None,
        "issue_title": None,
    }
    
    # Check for .current_issue file
    issue_file = os.path.join(project_path, ".current_issue")
    if os.path.exists(issue_file):
        try:
            with open(issue_file, "r") as f:
                import json
                data = json.load(f)
                results["has_active_issue"] = True
                results["issue_number"] = data.get("number")
                results["issue_title"] = data.get("title")
        except:
            pass
    
    return results


def determine_current_phase(project_path: str, repo_slug: str = None) -> Tuple[int, Dict]:
    """
    Determine the current pre-coding phase based on various indicators
    Returns (phase_number, details_dict)
    """
    details = {
        "phase": 1,
        "phase_name": "Analysis",
        "confidence": "low",
        "indicators": [],
        "next_steps": [],
        "warnings": [],
    }
    
    # Check feature docs
    docs_status = check_feature_docs(project_path)
    git_status = check_git_status(project_path)
    issue_status = check_issue_status(project_path, repo_slug)
    
    details["docs"] = docs_status
    details["git"] = git_status
    details["issue"] = issue_status
    
    # Determine phase based on indicators
    phase = 1
    
    # Phase 1: Analysis
    if not docs_status["found"]:
        phase = 1
        details["indicators"].append("❌ ไม่พบเอกสาร Feature ใน docs/features/")
        details["next_steps"].append("สร้างเอกสาร Analysis สำหรับ Feature ใหม่")
        details["confidence"] = "high"
        
    elif docs_status["found"] and not docs_status["has_analysis"]:
        phase = 1
        details["indicators"].append("📄 พบเอกสาร Feature แต่ยังไม่มี Analysis")
        details["next_steps"].append("เพิ่มหมวด Analysis ในเอกสาร")
        details["confidence"] = "medium"
        
    # Phase 2: Design
    elif docs_status["has_analysis"] and not docs_status["has_design"]:
        phase = 2
        details["indicators"].append("✅ Analysis เสร็จแล้ว")
        details["indicators"].append("❌ ยังไม่มี Design")
        details["next_steps"].append("ออกแบบ Database Schema")
        details["next_steps"].append("ออกแบบ System Architecture")
        details["next_steps"].append("ออกแบบ API Specification")
        details["confidence"] = "medium"
        
    # Phase 3: Planning
    elif docs_status["has_design"] and not docs_status["has_planning"]:
        phase = 3
        details["indicators"].append("✅ Analysis เสร็จแล้ว")
        details["indicators"].append("✅ Design เสร็จแล้ว")
        details["indicators"].append("❌ ยังไม่ได้วางแผน")
        details["next_steps"].append("ย่อยงานเป็น Tasks")
        details["next_steps"].append("ประเมินเวลา")
        details["next_steps"].append("กำหนด Definition of Done")
        details["confidence"] = "medium"
        
    # Phase 4: Coding
    elif docs_status["has_planning"] or git_status["is_feature_branch"]:
        phase = 4
        details["indicators"].append("✅ Analysis เสร็จแล้ว")
        details["indicators"].append("✅ Design เสร็จแล้ว")
        details["indicators"].append("✅ Planning เสร็จแล้ว")
        
        if git_status["is_feature_branch"]:
            details["indicators"].append(f"🌿 อยู่บน Feature Branch: {git_status['current_branch']}")
            if git_status["commits_ahead"] > 0:
                details["indicators"].append(f"📝 มี {git_status['commits_ahead']} commits")
                
        details["next_steps"].append("ดำเนินการ Coding ต่อ")
        details["confidence"] = "high"
    
    # Add warnings
    if git_status.get("has_uncommitted"):
        details["warnings"].append("⚠️ มี uncommitted changes")
        
    if not issue_status["has_active_issue"] and phase >= 4:
        details["warnings"].append("⚠️ ไม่พบ Active Issue - ควร link กับ Issue")
    
    details["phase"] = phase
    details["phase_name"] = PHASES[phase]["name"]
    
    return phase, details


def display_status(project_path: str, project_name: str, repo_slug: str = None):
    """
    Display the pre-coding status in a friendly format
    """
    print("\n" + "=" * 50)
    print("📊 Pre-Coding Status Checker")
    print("=" * 50)
    print(f"📂 Project: {project_name}")
    print(f"📍 Path: {project_path}")
    print("-" * 50)
    
    phase, details = determine_current_phase(project_path, repo_slug)
    
    # Display current phase
    print("\n🎯 Current Phase:")
    print("-" * 30)
    
    for p_num, p_info in PHASES.items():
        if p_num == phase:
            print(f"   {p_info['emoji']} [{p_num}] {p_info['name']} 👈 You are here")
        elif p_num < phase:
            print(f"   ✅ [{p_num}] {p_info['name']}")
        else:
            print(f"   ⬜ [{p_num}] {p_info['name']}")
    
    # Display indicators
    print("\n📌 Indicators:")
    print("-" * 30)
    for indicator in details["indicators"]:
        print(f"   {indicator}")
    
    # Display next steps
    if details["next_steps"]:
        print("\n📋 Next Steps:")
        print("-" * 30)
        for i, step in enumerate(details["next_steps"], 1):
            print(f"   {i}. {step}")
    
    # Display warnings
    if details["warnings"]:
        print("\n⚠️ Warnings:")
        print("-" * 30)
        for warning in details["warnings"]:
            print(f"   {warning}")
    
    # Show confidence level
    confidence_emoji = {"low": "🟡", "medium": "🟠", "high": "🟢"}
    print(f"\n📈 Confidence: {confidence_emoji.get(details['confidence'], '⚪')} {details['confidence'].upper()}")
    
    # Show latest doc if exists
    if details["docs"]["latest"]:
        latest = details["docs"]["latest"]
        print(f"\n📄 Latest Doc: {latest['name']}")
    
    print("\n" + "=" * 50)
    
    return phase, details


def interactive_checklist(project_path: str, project_name: str, repo_slug: str = None):
    """
    Interactive checklist mode for the current phase
    """
    phase, details = determine_current_phase(project_path, repo_slug)
    
    print(f"\n📋 Checklist for Phase {phase}: {PHASES[phase]['name']}")
    print("=" * 50)
    
    # Get checklist for current phase
    if phase == 1:
        checklist = ANALYSIS_CHECKS
    elif phase == 2:
        checklist = DESIGN_CHECKS
    elif phase == 3:
        checklist = PLANNING_CHECKS
    else:
        print("✅ คุณอยู่ใน Phase Coding แล้ว!")
        print("   ใช้เมนูอื่นเพื่อดำเนินการต่อ:")
        print("   - 1. Select Issue")
        print("   - 2. Create PR")
        print("   - 3. Code Review")
        return
    
    print("\nกรุณาตรวจสอบรายการต่อไปนี้:")
    print("-" * 30)
    
    completed = []
    for i, (key, name, description) in enumerate(checklist, 1):
        status = input(f"   [{i}] {name}\n       {description}\n       ✅ Done? (y/N/skip): ").strip().lower()
        if status == "y":
            completed.append(key)
            print(f"       ✅ Marked as done\n")
        elif status == "skip":
            print(f"       ⏩ Skipped\n")
        else:
            print(f"       ⬜ Not yet\n")
    
    # Summary
    print("\n📊 Summary:")
    print(f"   Completed: {len(completed)}/{len(checklist)}")
    
    if len(completed) == len(checklist):
        print(f"\n🎉 Phase {phase} Complete! Moving to Phase {phase + 1}...")
    else:
        remaining = len(checklist) - len(completed)
        print(f"\n📝 {remaining} items remaining in Phase {phase}")


def create_feature_doc(project_path: str):
    """
    Create a new feature documentation file
    """
    docs_path = os.path.join(project_path, "docs", "features")
    
    # Ensure directory exists
    os.makedirs(docs_path, exist_ok=True)
    
    # Find next number
    existing = glob.glob(os.path.join(docs_path, "*.md"))
    numbers = []
    for f in existing:
        basename = os.path.basename(f)
        if basename[0].isdigit():
            try:
                num = int(basename.split("_")[0])
                numbers.append(num)
            except:
                pass
    
    next_num = max(numbers) + 1 if numbers else 1
    
    # Get feature name
    feature_name = input("Feature Name (e.g., user_authentication): ").strip()
    if not feature_name:
        print("❌ Feature name required")
        return None
    
    # Create file
    filename = f"{next_num}_{feature_name}.md"
    filepath = os.path.join(docs_path, filename)
    
    # Template content
    template = f"""# Feature: {feature_name.replace('_', ' ').title()}

> 📅 Created: {datetime.now().strftime('%Y-%m-%d')}

---

## 1. Analysis

### 1.1 Requirement Analysis

**Problem Statement:**
[อธิบายปัญหาที่ต้องการแก้ไข]

**User Stories:**
- As a [role], I want to [action], so that [benefit]

**Acceptance Criteria:**
- [ ] [Criteria 1]
- [ ] [Criteria 2]

### 1.2 Feature Analysis

**User Flow:**
1. [Step 1]
2. [Step 2]

### 1.3 Impact Analysis

**Affected Components:**
- [ ] [Component 1]

### 1.4 Feasibility Analysis

| มิติ | ประเมิน | หมายเหตุ |
|------|---------|----------|
| Technical | ✅/⚠️/❌ | |
| Time | ✅/⚠️/❌ | |

### 1.5 Security Analysis

- [ ] [Security consideration]

### 1.6 Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| | | |

---

## 2. Design

### 2.1 Database Schema

```sql
-- Tables
```

### 2.2 System Architecture

```mermaid
flowchart TB
    A[Component A] --> B[Component B]
```

### 2.3 API Specification

| Endpoint | Method | Description |
|----------|--------|-------------|
| | | |

### 2.4 UI/UX Design

- [ ] Wireframes: [Link]

---

## 3. Planning

### 3.1 Task Breakdown

| # | Task | Estimate | Status |
|---|------|----------|--------|
| 1 | | | ⬜ |
| 2 | | | ⬜ |

### 3.2 Definition of Done

- [ ] Code complete
- [ ] Unit tests passed
- [ ] Documentation updated
- [ ] Code review passed

---

## 4. Notes

[Additional notes]
"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)
    
    print(f"\n✅ Created: {filepath}")
    print("   📝 Please fill in the template to complete Analysis phase")
    
    return filepath
