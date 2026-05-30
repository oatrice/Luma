# Walkthrough: Batch A (DevOps & Extended Data)

ผมได้ทำการลงมือพัฒนาตามแผน **Batch A** เพื่อตอบโจทย์ Issue #15 (CI/CD Auto-deploy) และ Issue #13 (Extended Meteorological Data) เสร็จสิ้นแล้วครับ นี่คือสรุปสิ่งที่มีการเปลี่ยนแปลงทั้งหมด

## 1. การดึงข้อมูลสภาพอากาศแบบละเอียด (Issue #13)
* **RainbowService Update:** ปรับปรุงฟังก์ชัน `predict_rain_by_location` ใน `rainbow.py` ให้ทำการคำนวณ:
  * **ความรุนแรง (Intensity):** โดยประเมินจากค่าสูงสุดของ `rain` (mm/h) ในพยากรณ์ หาก < 2.5 เป็น "เบา", 2.5 - 10.0 เป็น "ปานกลาง", > 10.0 เป็น "หนัก"
  * **ระยะเวลา (Duration):** คำนวณจากระยะเวลาตั้งแต่ช่วงที่ฝนตกแรกจนถึงช่วงสุดท้ายที่คาดการณ์ไว้ (หน่วยเป็นนาที)
* **Telegram Notification Update:** เปลี่ยนข้อความแจ้งเตือนใน `scheduler_tasks.py` และ `webhook.py` ให้มีอิโมจิน่ารักขึ้น และบอกความรุนแรงและระยะเวลาได้อย่างชัดเจน:
  > 🌧️ ฝนกำลังเคลื่อนมาทางทิศของคุณ จะเริ่มตกในอีก X นาที
  > 💧 ความรุนแรง: ปานกลาง (Moderate)
  > ⏱️ คาดว่าจะตกต่อเนื่องประมาณ: 40 นาที
* **TDD & Tests:** เพิ่ม Unit Test เข้าไปใน `test_services.py` 2 เคสสำหรับการตกหนัก (Heavy) และตกเบา (Light) ซึ่งโค้ดผ่านการทดสอบทั้งหมด 100%

## 2. โครงสร้างพื้นฐานและการ Deploy (Issue #15)
* **GitLab CI Deploy Stage:** เพิ่ม `deploy_cloud_run` stage ในไฟล์ `.gitlab-ci.yml` โดยกำหนดค่าให้:
  * ทำการ Deploy ไปที่ Cloud Run อัตโนมัติ (`gcloud run deploy fontokmai-api`) เมื่อมีการ push ลง `main`
  * อัปเดต Telegram Webhook ให้อัตโนมัติโดยดึงค่า URL ปัจจุบันจาก Cloud Run (ป้องกันบอทตอบกลับไม่ได้เมื่อ Deploy URL มีการเปลี่ยนแปลง)
* **Two Bots Strategy Docs:** สร้างไฟล์ `docs/development_guide.md` เพื่อใช้อธิบายขั้นตอนการ Setup "Dev Bot" คู่กับ `localtunnel` เพื่อการพัฒนา Locally ได้อย่างปลอดภัย ไม่ต้องกังวลว่า Webhook จะตีกับตัว Production 

## 3. การรองรับ External APIs
* ได้ทำการสร้าง GitLab Issue อันใหม่ชื่อ **Feature: Integrate external meteorological APIs (Open-Meteo, TMD) for enhanced data (Wind, Accurate Intensity)** สำหรับการต่อยอดในการดึงข้อมูลลม (Wind speed) ตามที่คุณรีเควส และได้ทำ Backlink กลับไปยัง Issue #13 ไว้แล้ว

---

### ขั้นตอนต่อไปของคุณ
1. ตั้งค่า GitLab CI/CD Variables: ใส่ `GCP_PROJECT_ID` และ `GCP_SA_KEY` ใน Settings > CI/CD ของ Repository บน GitLab เพื่อให้ท่อ Deploy พร้อมทำงาน
2. สร้าง Merge Request จาก branch `feat/batch-a` นี้และ Merge เข้า `main` เพื่อดูผลการ Auto-deploy ของจริงได้เลยครับ!
