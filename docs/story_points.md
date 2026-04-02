# Story Points Convention

> ต้องการเวอร์ชันอ่านเร็ว: ดู [Story Points Cheat Sheet](/Users/oatrice/Software-projects/Luma/docs/story_points_cheatsheet.md)

## หลักการ: Story Points ≠ Man-days

> **Story Points วัดความซับซ้อน (Complexity) ไม่ใช่เวลา (Time)**

ตาม Agile standard แล้ว Story Points และ Man-days คือคนละสิ่งกัน:

- **Story Points** = relative measure ของ effort, complexity, และ uncertainty
- **Man-days** = เวลาจริง (calendar time) ที่ใช้ทำงาน

การแปลง 1 point = 1 day แบบ 1:1 ที่เคยใช้ก่อนหน้านี้ถูกยกเลิกแล้ว

---

## Fibonacci Scale ที่ใช้

```
0.5 pt  →  ไม่มีใน standard scale (ห้ามใช้)
1  pt   →  งานเล็กมาก (refactor, แก้ text, minor fix)
2  pt   →  งานเล็ก (bug fix, simple UI)
3  pt   →  งานกลาง (sub-feature, component เล็ก)
5  pt   →  งานที่ต้องวางแผน (feature พอดี)
8  pt   →  งานใหญ่ (ควร spike ก่อน)
13 pt   →  ใหญ่มาก → ต้อง break ลงก่อน estimate
21 pt   →  Epic → ห้าม assign โดยตรง ต้อง decompose
```

> 💡 งานที่รู้สึกว่าเล็กกว่า 1 point → ให้ assign **1 point** แล้วปล่อยไป

---

## Conversion Table (สำหรับ Planning เท่านั้น)

| Story Points | Man-days (approx.) | เวลาจริง (approx.) |
|---|---|---|
| 1 | 0.5 | 4 ชั่วโมง |
| 2 | 1.0 | 1 วัน |
| 3 | 1.5 | 1-2 วัน |
| 5 | 3.0 | 3 วัน |
| 8 | 5.0 | 1 สัปดาห์ |
| 13 | 10.0 | 2 สัปดาห์ |
| 21 | 15.0 | 3 สัปดาห์ |

> ⚠️ **หมายเหตุ**: ค่า Man-days นี้ใช้เพื่อ rough planning เท่านั้น
> อย่านำไปใช้ track เวลาจริง ให้ใช้ `actual_mandays` field แยกต่างหาก

---

## Spike คืออะไร?

**Spike** คือ time-boxed research task เพื่อลด uncertainty ก่อน estimate จริง

- ใช้เมื่อทีมไม่มั่นใจว่างานจะซับซ้อนแค่ไหน
- กำหนดเวลา spike ชัดเจน เช่น "1 วัน"
- Output = ข้อมูลพอ estimate งานจริงได้

**ตัวอย่าง:**
```
🔬 [SPIKE] Research Video Streaming approach
   Time-box: 1 วัน
   Output: ตัดสินใจ HLS vs DASH + estimate ที่แม่นขึ้น
```

---

## Implementation

การแปลง Story Points → Man-days ใช้ `points_to_mandays()` ใน
`luma_core/issue_metrics.py` ผ่าน `POINTS_TO_MANDAYS` dict

```python
POINTS_TO_MANDAYS = {1: 0.5, 2: 1.0, 3: 1.5, 5: 3.0, 8: 5.0, 13: 10.0, 21: 15.0}
```
