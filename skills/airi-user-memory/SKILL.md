---
name: airi-user-memory
version: 1.0.0
description: Maintain persistent user facts, relationship context, personal preferences, and honorific preferences across sessions in MEMORY.md.
author: Airi Sensei Team
tags: [memory, personalization, facts, profile]
---

# Airi User Memory Skill (`airi-user-memory`)

## 1. Overview
This skill implements Airi Sensei's persistent long-term memory. It captures key facts revealed by the user (name, nicknames, food preferences, coding habits, address wishes) and stores them in `workspace/MEMORY.md`.

---

## 2. When to Use
- When the user introduces themselves: *"Anh tên là Tiến nhé"*
- When the user asks for a specific addressing style: *"Từ giờ gọi anh là anh yêu nha"*
- When the user shares personal facts: *"Anh thích uống cà phê sữa ít đường"*
- When the user asks Airi what she remembers about them: *"Airi nhớ gì về anh không?"*

---

## 3. Storage Format
Facts are organized in `workspace/MEMORY.md` by User ID:

```markdown
# Airi Sensei Long-Term Memory (MEMORY.md)

## User Profile & Facts (User ID: 5556841083)
- **ten_goi**: Tiến *(Updated: 2026-11-03T04:00:00+00:00)*
- **cach_xung_ho**: anh yêu *(Updated: 2026-11-03T04:00:00+00:00)*
- **so_thich**: Lập trình AI, uống cà phê sữa ít đường *(Updated: 2026-11-03T04:00:00+00:00)*
```

---

## 4. Input Specifications
- **`user_id`** *(integer, required)*: The Telegram user ID.
- **`key`** *(string, required)*: Normalized fact key (e.g. `ten_goi`, `cach_xung_ho`, `so_thich`).
- **`value`** *(string, required)*: The value to record.

---

## 5. Expected Output
- Airi acknowledges the remembered fact with affection and warmth:
  *"Dạ, Airi đã ghi nhớ vào trái tim rồi nè! Từ nay em sẽ gọi anh là **anh yêu** nhé! 🌸✨"*

---

## 6. Error Handling
- If `key` or `value` is empty, gently ask the user to clarify.
- File write errors must be logged without interrupting the conversational flow.
