# Implementation Plan: Tracking Estimate Points, Mandays, and Effort

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `luma_core/state.py`: จะมีการเพิ่มโมเดลข้อมูลสำหรับเก็บเมตริกการติดตาม (Estimate Points, Mandays, Effort Level) ลงในโครงสร้าง `LumaState` ที่มีอยู่
    - `luma_core/state_manager.py`: จะมีการอัปเดตเพื่อจัดการการอ่าน/เขียนข้อมูล `LumaState` ที่มีเมตริกใหม่
    - `luma_core/actions.py`: จะมีการเพิ่มฟังก์ชันสำหรับป้อน/แก้ไขเมตริก และฟังก์ชันสำหรับการเรียกใช้การรวบรวม/แสดงผลเมตริก
    - `luma_core/ui.py`: จะมีการเพิ่มอินเทอร์เฟซผู้ใช้สำหรับ CLI เพื่อให้ผู้ใช้สามารถป้อนข้อมูลเมตริก และแสดงผลสรุปเมตริก
- **New Components**:
    - `luma_core/metrics.py` (หรืออาจจะรวมอยู่ใน `luma_core/models.py` ถ้ามี): โมเดล Pydantic สำหรับ `IssueMetrics` และ `ProjectMetrics`
    - `luma_core/metric_aggregator.py`: โมดูลใหม่สำหรับจัดการการรวบรวมเมตริกในระดับ Issue และ Project
- **Dependencies**:
    - Pydantic สำหรับโมเดลข้อมูล
    - โมดูล `state` และ `state_manager` ที่มีอยู่สำหรับ persistent storage
    - โมดูล `ui` และ `actions` ที่มีอยู่สำหรับ interaction layer

### Data Model Changes
```python
# luma_core/metrics.py (New File, or added to luma_core/models.py)
from pydantic import BaseModel, Field
from typing import Optional

class IssueMetrics(BaseModel):
    issue_id: str
    estimate_points: Optional[int] = None
    estimated_mandays: Optional[float] = None
    actual_mandays: Optional[float] = None
    effort_level: Optional[str] = None # e.g., "Low", "Medium", "High"

class ProjectMetricsSummary(BaseModel):
    project_name: str
    total_estimate_points: int = 0
    total_estimated_mandays: float = 0.0
    total_actual_mandays: float = 0.0
    average_effort_level: Optional[str] = None # Or a more complex aggregation if needed

# luma_core/state.py (Modified)
from typing import Dict
from luma_core.metrics import IssueMetrics # Assuming metrics.py

class Issue(BaseModel):
    # ... existing fields ...
    metrics: Optional[IssueMetrics] = None # New field

class Project(BaseModel):
    # ... existing fields ...
    issues: Dict[str, Issue] # Assuming issues are stored in a dict by ID

class LumaState(BaseModel):
    projects: Dict[str, Project]
    # ... existing fields ...
```

---

## 2. Step-by-Step Implementation

### Step 1: Define and Integrate Issue Metrics Data Model
- **Docs**: อัปเดตเอกสารภายในเกี่ยวกับโครงสร้างข้อมูล `LumaState`
- **Code**:
    - สร้างไฟล์ `luma_core/metrics.py` (หรือเพิ่มในไฟล์โมเดลที่มีอยู่) เพื่อกำหนดโมเดล `IssueMetrics` และ `ProjectMetricsSummary` โดยใช้ Pydantic
    - แก้ไข `luma_core/state.py` เพื่อเพิ่มฟิลด์ `metrics: Optional[IssueMetrics]` ในคลาส `Issue`
- **Tests**:
    - เขียน Unit test สำหรับ `IssueMetrics` model เพื่อยืนยันการสร้าง การกำหนดค่า และการแปลงเป็น JSON ได้อย่างถูกต้อง

### Step 2: Implement Persistence for Issue Metrics
- **Docs**: เพิ่มบันทึกการเปลี่ยนแปลงในเอกสารที่เกี่ยวข้องกับการจัดเก็บข้อมูล
- **Code**:
    - แก้ไข `luma_core/state_manager.py` เพื่อให้แน่ใจว่าฟิลด์ `metrics` ใหม่ใน `Issue` ถูกโหลดและบันทึกอย่างถูกต้องไปยัง `.luma_state.json`
- **Tests**:
    - เขียน Unit test สำหรับ `state_manager` เพื่อยืนยันว่า `IssueMetrics` สามารถบันทึกและโหลดจาก `.luma_state.json` ได้อย่างถูกต้องและคงอยู่ตลอดเซสชัน

### Step 3: Implement CLI for Inputting/Updating Issue Metrics
- **Docs**: อัปเดตเอกสารคู่มือผู้ใช้เกี่ยวกับคำสั่งใหม่สำหรับป้อนและแก้ไขเมตริก
- **Code**:
    - แก้ไข `luma_core/actions.py` เพื่อเพิ่มฟังก์ชันใหม่ (เช่น `set_issue_metrics`) ที่รับ `issue_id`, `estimate_points`, `estimated_mandays`, `actual_mandays`, `effort_level` และอัปเดต `LumaState`
    - แก้ไข `luma_core/ui.py` เพื่อเพิ่มคำสั่ง CLI ใหม่ (เช่น `luma issue metrics set <issue_id> --points <value> --em <value> --am <value> --effort <level>`) และ UI สำหรับการโต้ตอบผู้ใช้
- **Tests**:
    - เขียน Unit test สำหรับ `actions.py` เพื่อยืนยันว่าฟังก์ชัน `set_issue_metrics` ทำงานได้อย่างถูกต้อง รวมถึงการจัดการ edge cases (เช่น issue_id ไม่ถูกต้อง)
    - เขียน Integration test โดยจำลองการป้อนข้อมูลผ่าน CLI เพื่อยืนยันว่าเมตริกถูกจัดเก็บและอัปเดตอย่างถูกต้อง

### Step 4: Implement Metric Aggregation Logic
- **Docs**: สร้างเอกสารประกอบสำหรับโมดูล `metric_aggregator` ใหม่
- **Code**:
    - สร้างไฟล์ `luma_core/metric_aggregator.py`
    - ใน `metric_aggregator.py` ให้สร้างฟังก์ชัน (เช่น `aggregate_project_metrics`, `aggregate_all_metrics`) ที่วนซ้ำผ่าน `LumaState.projects` และ `LumaState.issues` เพื่อคำนวณ `ProjectMetricsSummary`
- **Tests**:
    - เขียน Unit test สำหรับ `metric_aggregator.py` เพื่อยืนยันการคำนวณผลรวมและค่าเฉลี่ยที่ถูกต้อง รวมถึงการจัดการกรณีที่ไม่มีข้อมูลเมตริก

### Step 5: Implement CLI for Displaying and Exporting Metrics
- **Docs**: อัปเดตเอกสารคู่มือผู้ใช้เกี่ยวกับคำสั่งใหม่สำหรับดูและส่งออกเมตริก
- **Code**:
    - แก้ไข `luma_core/actions.py` เพื่อเพิ่มฟังก์ชันใหม่ (เช่น `get_metrics_summary`, `export_metrics`) ที่เรียกใช้ `metric_aggregator` และเตรียมข้อมูลสำหรับการแสดงผลหรือส่งออก
    - แก้ไข `luma_core/ui.py` เพื่อเพิ่มคำสั่ง CLI ใหม่ (เช่น `luma metrics summary [project_name]`, `luma metrics export --format json/csv`) สำหรับแสดงผลสรุปและส่งออกข้อมูล
- **Tests**:
    - เขียน Unit test สำหรับ `actions.py` เพื่อยืนยันว่าฟังก์ชัน `get_metrics_summary` และ `export_metrics` เรียกใช้ aggregator อย่างถูกต้องและส่งคืนข้อมูลในรูปแบบที่คาดไว้
    - เขียน Integration test โดยจำลองการเรียกใช้ CLI เพื่อดูและส่งออกเมตริก และตรวจสอบรูปแบบผลลัพธ์

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests
- [x] Unit Tests:
    - `tests/test_metrics.py`: สำหรับ `IssueMetrics` และ `ProjectMetricsSummary` model
    - `tests/test_state_manager.py`: สำหรับการ persistence ของ `IssueMetrics` ใน `LumaState`
    - `tests/test_actions.py`: สำหรับฟังก์ชันการป้อน/อัปเดตเมตริกและฟังก์ชันการรวบรวม/ส่งออก
    - `tests/test_metric_aggregator.py`: สำหรับฟังก์ชันการรวบรวมเมตริก
- [ ] Integration Tests:
    - ทดสอบเวิร์กโฟลว์เต็มรูปแบบของการป้อนเมตริก การบันทึก การโหลด และการรวบรวมผ่าน CLI

### Manual Verification
- [ ] **การป้อนและอัปเดตเมตริก**:
    - [ ] ป้อน Estimate Points, Estimated Mandays, Effort level สำหรับ Issue ใหม่
    - [ ] ตรวจสอบว่าเมตริกถูกบันทึกอย่างถูกต้องโดยการดู Issue นั้นอีกครั้ง
    - [ ] อัปเดต Estimated Mandays และป้อน Actual Mandays สำหรับ Issue เดียวกัน
    - [ ] ปิดและเปิด CLI ใหม่เพื่อยืนยันว่าเมตริกยังคงอยู่ (persistence)
- [ ] **การรวบรวมเมตริก**:
    - [ ] สร้างหลาย Issue ใน Project เดียวกัน และป้อนเมตริกที่แตกต่างกัน
    - [ ] เรียกใช้คำสั่ง `luma metrics summary <project_name>` และยืนยันว่าผลรวมถูกต้อง
    - [ ] สร้าง Issue ในหลาย Project และป้อนเมตริก
    - [ ] เรียกใช้คำสั่ง `luma metrics summary` (สำหรับทุก Project) และยืนยันผลรวมถูกต้อง
- [ ] **การส่งออกข้อมูล**:
    - [ ] ส่งออกข้อมูลเมตริกเป็น JSON และ CSV
    - [ ] ตรวจสอบโครงสร้างและเนื้อหาของไฟล์ที่ส่งออกว่าถูกต้องตามที่คาดไว้