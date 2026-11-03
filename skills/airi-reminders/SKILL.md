---
name: airi-reminders
version: 1.0.0
description: Schedule and manage automated time-based reminders delivered directly to the user's Telegram chat via OpenClaw Automations.
author: Airi Sensei Team
tags: [reminders, automations, cron, schedule, notifications]
---

# Airi Reminders Skill (`airi-reminders`)

## 1. Overview
The Reminders skill connects Airi Sensei to OpenClaw's native automations and scheduler engine. It enables scheduling one-shot timers (e.g., "in 30 minutes") or recurring cron jobs that trigger active messages delivered directly to the user on Telegram.

---

## 2. When to Use
- When the user sets a relative reminder:
  - *"Nhắc anh uống nước sau 30 phút nữa nhé"*
  - *"Sau 1 tiếng nhắc anh vào họp dự án"*
- When the user sets a specific time reminder:
  - *"Hẹn 8 giờ sáng mai nhắc anh nộp báo cáo"*
- When the user lists their active reminders:
  - *"Anh có lịch nhắc nhở nào sắp tới không?"*

---

## 3. Execution Workflow
1. Parse user's time intent relative to GMT+7 (`Asia/Ho_Chi_Minh`).
2. Calculate target ISO-8601 timestamp.
3. Register job with OpenClaw Automations engine (`openclaw automations add --at ...`).
4. Persist job in `workspace/automations/reminders.json`.
5. When the timer fires, the OpenClaw scheduler wakes up and delivers the formatted reminder message into Telegram chat.

---

## 4. Input Specifications
- **`user_id`** *(integer, required)*: The recipient's Telegram user ID.
- **`minutes_from_now`** *(integer, optional)*: Relative minutes from current time.
- **`target_time_iso`** *(string, optional)*: Explicit target timestamp.
- **`message`** *(string, required)*: Content of the reminder.

---

## 5. Expected Output
- **Acknowledgment:**
  *"Dạ em đã hẹn giờ nhắc nhở cho anh sau 30 phút nữa nhé: 'Đi uống nước'. Đúng giờ em sẽ gọi anh nha! ⏰🌸"*
- **Delivered Message (at due time):**
  ```markdown
  ⏰ **Airi nhắc nhở anh nè:**

  _Đi uống nước_

  — Airi Sensei 🌸
  ```

---

## 6. Error Handling
- Validate that the target time is strictly in the future.
- If parsing fails, ask the user to specify the exact number of minutes or target hour.
