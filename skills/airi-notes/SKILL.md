---
name: airi-notes
version: 1.0.0
description: Manage personal user notes, meeting minutes, and reminders in structured Markdown files within the workspace.
author: Airi Sensei Team
tags: [notes, memory, organization, workspace]
---

# Airi Notes Skill (`airi-notes`)

## 1. Overview
The Notes skill empowers Airi Sensei to serve as a personal secretary. It saves, lists, searches, and deletes structured Markdown notes stored in per-user directories under `workspace/notes/user_<user_id>/`.

---

## 2. When to Use
- When the user asks Airi to take down a note or remember a task:
  - *"Lưu ghi chú: Mua tài liệu OpenClaw ngày mai"*
  - *"Ghi lại giúp anh ý tưởng này: ... "*
- When the user wants to review their saved notes:
  - *"Xem danh sách ghi chú của anh"*
  - *"Anh có ghi chú nào về dự án X không?"*
- When the user requests deleting a note:
  - *"Xóa ghi chú số 2"*

---

## 3. Storage Convention
Notes are stored on the persistent disk as individual Markdown files:
`workspace/notes/user_<user_id>/note_<note_id>.md`

File format:
```markdown
---
id: 1
user_id: 5556841083
title: "Ý tưởng sản phẩm"
created_at_utc: "2026-11-03T04:30:00+00:00"
---

# Ý tưởng sản phẩm

1. Nâng cấp bot lên kiến trúc OpenClaw 3.0.
2. Tích hợp mô hình Groq 120B siêu tốc.
```

---

## 4. Input Specifications
- **`action`** *(string, required)*: One of `["save", "list", "delete", "search"]`.
- **`title`** *(string, optional)*: Note title (required when `action="save"`).
- **`content`** *(string, optional)*: Detailed note body (required when `action="save"`).
- **`note_id`** *(integer, optional)*: Target ID when `action="delete"`.
- **`query`** *(string, optional)*: Search term when `action="search"`.

---

## 5. Expected Output
- **Save:** Confirmation message with assigned Note ID:
  *"Dạ em đã lưu ghi chú #3 ('Ý tưởng sản phẩm') vào sổ tay của anh rồi nhé! 📝✨"*
- **List:** Formatted list of existing notes:
  ```markdown
  📝 **Sổ tay ghi chú của anh:**
  • #1: **Học OpenClaw** (Ngày tạo: 03/11/2026)
  • #2: **Lịch bảo trì** (Ngày tạo: 02/11/2026)
  ```
- **Delete:** Confirmation that note #ID was removed.

---

## 6. Error Handling
- If a requested note ID is not found: Notify the user with kindness and offer to list active notes.
- If directory permissions fail: Gracefully alert the administrator.
