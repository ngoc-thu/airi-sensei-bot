# Data Migration Manual: Legacy SQLite to OpenClaw v3.0

## 1. Safety Guarantees & Prerequisites

1. **Non-Destructive Guarantee:**
   - The original database (`data/airi_memory.db`) is opened strictly with SQLite URI parameter `mode=ro` (read-only).
   - No `DROP`, `DELETE`, `UPDATE`, or schema mutation is executed on the legacy database during migration.
2. **Atomic Backup Requirement:**
   - Before executing migration, an atomic snapshot is generated via `scripts/backup_legacy_db.py`.
   - The backup generates an immutable file under `data/legacy_backup/` accompanied by a SHA-256 hash manifest.
3. **Idempotence:**
   - `scripts/migrate_legacy_data.py` is fully idempotent. Running it repeatedly updates existing records in place without duplicating user facts, note files, or reminder jobs.

---

## 2. Table-by-Table Migration Logic

### 2.1 User Facts (`user_facts`)
- **Legacy Schema:** `user_facts (user_id INTEGER, key TEXT, value TEXT, updated_at REAL, PRIMARY KEY (user_id, key))`
- **Target Representation:** Appended and indexed in `workspace/MEMORY.md` under `## User Profile & Facts (User ID: <user_id>)`.
- **Transformation:**
  ```markdown
  - **ten_goi**: Tiến *(Updated: 2026-11-03T04:00:00+00:00)*
  - **cach_xung_ho**: anh yêu *(Updated: 2026-11-03T04:00:00+00:00)*
  ```
- **Idempotence:** If a fact key already exists for the user, regex replacement updates the value in place instead of creating duplicate bullet points.

### 2.2 Notes (`notes`)
- **Legacy Schema:** `notes (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, content TEXT, created_at REAL)`
- **Target Representation:** Isolated markdown files at `workspace/notes/user_<user_id>/note_<id>.md`.
- **File Format:**
  ```markdown
  ---
  legacy_id: 1
  user_id: 5556841083
  title: "Tài liệu OpenClaw"
  created_at_utc: "2026-11-03T04:00:00+00:00"
  ---

  # Tài liệu OpenClaw

  Nội dung ghi chú cá nhân của người dùng...
  ```
- **Idempotence:** Overwrites `note_<id>.md` deterministically.

### 2.3 Reminders (`reminders`)
- **Legacy Schema:** `reminders (id INTEGER PRIMARY KEY, user_id INTEGER, reminder_text TEXT, remind_at REAL, is_sent INTEGER, created_at REAL)`
- **Target Representation:**
  - Active reminders (`is_sent = 0` and `remind_at > now`) -> `workspace/automations/reminders.json`.
  - Delivered or expired reminders -> `workspace/automations/archived_reminders.json`.
- **JSON Job Structure:**
  ```json
  {
    "id": "legacy_reminder_1",
    "legacy_id": 1,
    "user_id": 5556841083,
    "message": "Uống nước",
    "scheduled_at_timestamp": 1793610000.0,
    "scheduled_at_iso": "2026-11-03T06:00:00+00:00",
    "timezone": "Asia/Ho_Chi_Minh",
    "status": "pending",
    "action": {
      "channel": "telegram",
      "recipient": "5556841083",
      "text": "⏰ **Airi nhắc nhở anh nè:**\n\n_Uống nước_\n\n— Airi Sensei 🌸"
    }
  }
  ```

### 2.4 Messages (`messages`)
- **Legacy Schema:** `messages (id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, content TEXT, timestamp REAL)`
- **Policy:** Raw messages are **not** imported directly into the active prompt session to prevent context window bloat and token exhaustion.
- **Audit:** An archived summary containing total message counts, date ranges, and user IDs is written to `workspace/memory/legacy_conversations_summary.json`.

---

## 3. Step-by-Step Migration Execution

### Step 1: Execute Backup
```bash
python3 scripts/backup_legacy_db.py --source data/airi_memory.db --target data/legacy_backup
```
Verify the output JSON displays `"status": "success"` and confirms matching row counts.

### Step 2: Perform Dry-Run Validation
```bash
python3 scripts/migrate_legacy_data.py --db-path data/airi_memory.db --workspace workspace --dry-run
```
Review the projected migration counts without writing files to disk.

### Step 3: Execute Live Migration
```bash
python3 scripts/migrate_legacy_data.py --db-path data/airi_memory.db --workspace workspace
```

### Step 4: Validate Destination Files
```bash
ls -la workspace/notes/
cat workspace/MEMORY.md
cat workspace/automations/reminders.json
```

---

## 4. Disaster Recovery & Rollback

If data needs to be restored to the legacy format:
1. Locate the backup database in `data/legacy_backup/airi_memory_<timestamp>.db`.
2. Verify its checksum matches `data/legacy_backup/airi_memory_<timestamp>_metadata.json`.
3. Copy it back to `data/airi_memory.db`.
