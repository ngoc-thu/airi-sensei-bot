# USER.md: User Profile & Context Preferences

## Default Owner Profile
- **Primary Owner ID:** `5556841083`
- **Owner Name / Call Sign:** Tiến (Master / Quản trị viên)
- **Language:** Tiếng Việt (Vietnamese)
- **Default Timezone:** `Asia/Ho_Chi_Minh` (GMT+7)

---

## Addressing Guidelines
- Refer to the user according to their configured preference or most recent instruction recorded in `MEMORY.md`.
- If no custom honorific is recorded, address respectfully as *"anh"* or *"bạn"*.
- If the user specifies a nickname or honorific, acknowledge it, log it via the `remember_user_fact` skill, and persist the preference across all future dialogues.

---

## User Preferences Storage
- Persistent user profile facts are maintained in `MEMORY.md` under `# Profile & Facts: User <user_id>`.
- Any modification to personal facts, dietary preferences, coding languages, or daily routines should be indexed by user ID.
