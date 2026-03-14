"""
🔔 Luma Notifier — ส่ง Task Completion Notification ไปยัง Telegram ผ่าน Akasa Backend

เรียก POST /api/v1/notifications/task-complete เพื่อแจ้งผลงานเมื่อ Luma action เสร็จสิ้น
ถ้า env vars ไม่ได้ตั้งค่า → skip อย่างเงียบเฉย (ไม่ crash)
"""

import os
from typing import Optional

import requests

from . import config

# --- Configuration (re-exported from config for test patching) ---
AKASA_API_URL = config.AKASA_API_URL
AKASA_API_KEY = config.AKASA_API_KEY
AKASA_CHAT_ID = config.AKASA_CHAT_ID


def notify_task_complete(
    project: str,
    task: str,
    status: str,
    duration: Optional[str] = None,
    message: Optional[str] = None,
    link: Optional[str] = None,
) -> bool:
    """
    ส่ง notification ไปยัง Akasa Backend → Telegram

    Args:
        project: ชื่อโปรเจกต์
        task: คำอธิบาย action ที่เพิ่งเสร็จ
        status: "success" | "failure" | "partial"
        duration: เวลาที่ใช้ (optional)
        message: รายละเอียดเพิ่มเติม (optional)
        link: URL ที่เกี่ยวข้อง (optional)

    Returns:
        True ถ้าส่งสำเร็จ, False ถ้า skip หรือ error
    """
    if not AKASA_CHAT_ID:
        return False

    payload: dict = {
        "project": project,
        "task": task,
        "status": status,
        "chat_id": AKASA_CHAT_ID,
        "source": "Luma CLI",
    }

    if duration is not None:
        payload["duration"] = duration
    if message is not None:
        payload["message"] = message
    if link is not None:
        payload["link"] = link

    headers = {"X-Akasa-API-Key": AKASA_API_KEY}

    try:
        response = requests.post(
            f"{AKASA_API_URL}/api/v1/notifications/task-complete",
            json=payload,
            headers=headers,
            timeout=5.0,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"⚠️ Notification failed (non-blocking): {e}")
        return False
