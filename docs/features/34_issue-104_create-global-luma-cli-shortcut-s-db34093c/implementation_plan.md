# แผนการสร้าง Global Luma CLI Shortcut

สร้าง executable script สำหรับ luma ไว้ที่ `~/.local/bin/luma` เพื่อให้สามารถเรียกใช้งาน Luma ได้จากทุกไดเรกทอรี และลบ local wrapper script เดิมในโปรเจกต์ `FonMaYang`

## รายละเอียดการเปลี่ยนแปลง

### 1. สร้างไฟล์ใหม่ที่ Global Bin Directory

#### [NEW] [luma](file:///Users/oatrice/.local/bin/luma)
สร้างไฟล์สคริปต์ zsh โดยมีเนื้อหาดังนี้:
- ระบุ `LUMA_DIR="/Users/oatrice/Software Project/Luma"`
- ตรวจสอบความถูกต้องของ virtual environment (`venv`) ของ Luma
- โหลดและส่งออกไฟล์คอนฟิกูเรชัน `.env` จากโฟลเดอร์ของ Luma (ถ้ามี)
- รันไฟล์ Python `main.py` โดยใช้ Python จาก venv และส่งต่อพารามิเตอร์ทั้งหมด (`$@`) พร้อมทั้งคง Working Directory เดิมไว้

### 2. ลบ Local Wrapper ในโปรเจกต์ FonMaYang

#### [DELETE] [luma](file:///Users/oatrice/Software%20Project/FonMaYang/luma)
ลบสคริปต์ wrapper ท้องถิ่นหลังสร้างและตรวจสอบคำสั่ง global luma ทำงานได้ถูกต้องแล้ว

---

## ขั้นตอนการตรวจสอบ (Verification Plan)

1. ตรวจสอบการสร้างไฟล์และการตั้งค่าสิทธิ์ executable (`chmod +x ~/.local/bin/luma`)
2. ทดลองรันคำสั่ง `luma` จากไดเรกทอรีอื่นๆ นอกเหนือจาก Luma และ FonMaYang
3. ตรวจสอบว่าคำสั่งสามารถอ่านค่า `.env` และส่งอาร์กิวเมนต์ไปยัง Luma ได้ถูกต้อง
4. ลบไฟล์ local wrapper และทดสอบรันใหม่อีกครั้ง
