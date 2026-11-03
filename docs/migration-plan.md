# Airi Sensei v2.5 to v3.0 Migration Plan

## 1. Overview & Strategy

This migration plan outlines the exact, step-by-step procedure for upgrading Airi Sensei from version 2.5 (custom Python ReAct bot) to version 3.0 (OpenClaw Agent Runtime).

The migration follows four immutable rules:
1. **Never delete or overwrite original data:** The legacy SQLite database is backed up and kept strictly read-only.
2. **Zero Polling Contention:** The legacy Python bot process and OpenClaw Gateway must never poll the Telegram bot token concurrently.
3. **Idempotence:** Every migration script must be safe to re-run multiple times without producing duplicate records.
4. **Instant Rollback Readiness:** A complete rollback mechanism is documented and verified before production cutover.

---

## 2. Migration Phases Timeline

```mermaid
flowchart LR
    P0["Phase 0: Audit & Docs"] --> P1["Phase 1: Backup Legacy DB"]
    P1 --> P2["Phase 2: OpenClaw Scaffolding"]
    P2 --> P3["Phase 3: Persona & Skills"]
    P3 --> P4["Phase 4: Data Migration Dry-Run"]
    P4 --> P5["Phase 5: Render Deployment"]
    P5 --> P6["Phase 6: Cutover & Validation"]
```

---

## 3. Detailed Phase Breakdown

### Phase 0: Audit & Baseline Verification (Completed)
- Inspect all files, test suite, and configuration.
- Confirm all 42 unit tests pass in existing Python codebase.
- Document v3 architecture, feature mapping, and Render deployment specifications.

### Phase 1: Pre-Migration Backup & Safety
- **Objective:** Create a verified, immutable snapshot of `/data/airi_memory.db`.
- **Tool:** `scripts/backup_legacy_db.py`.
- **Procedure:**
  1. Acquire an SQLite read-only transaction or filesystem snapshot.
  2. Compute SHA-256 checksum of the source database.
  3. Copy to `/data/legacy_backup/airi_memory_YYYYMMDD_HHMMSS.db`.
  4. Write `backup_metadata.json` documenting original size, row counts, and checksum.
  5. Verify backup integrity by opening the backup database and counting rows.

### Phase 2: OpenClaw Configuration Scaffolding
- **Objective:** Establish the OpenClaw configuration file (`openclaw.json`) and workspace directory.
- **Key Files:**
  - `openclaw.json`: Gateway port, binding, Telegram channel driver, provider fallbacks, tool permissions.
  - `.env.example`: Complete template for all required runtime environment variables without real secrets.
  - Directory structure: `/data/.openclaw/` and `/data/workspace/`.

### Phase 3: Persona, Instructions, & Custom Skills Scaffolding
- **Objective:** Implement Airi Sensei's Vietnamese personality and custom tools within the OpenClaw workspace.
- **Key Deliverables:**
  - `workspace/AGENTS.md`: Operational principles, research instructions, factuality rules.
  - `workspace/SOUL.md`: Persona essence, Vietnamese conversational tone, honorific handling.
  - `workspace/USER.md`: User profile conventions and default addressing.
  - `workspace/TOOLS.md`: Local tool conventions and usage rules.
  - `skills/airi-image/SKILL.md`: Pollinations Flux/Turbo art generator.
  - `skills/airi-notes/SKILL.md`: Markdown-based notes management.
  - `skills/airi-user-memory/SKILL.md`: Long-term fact persistence.
  - `skills/airi-reminders/SKILL.md`: Native automations integration.
  - `skills/research/SKILL.md`: Deep search + webpage extraction pipeline.
  - `skills/document-generation/SKILL.md`: Safe calculation and document generator.

### Phase 4: Legacy Data Migration Execution
- **Objective:** Migrate legacy records from SQLite into OpenClaw's native formats.
- **Tool:** `scripts/migrate_legacy_data.py`.
- **Transformation Rules:**
  1. **User Facts (`user_facts`):**
     - Extract `(user_id, key, value, updated_at)`.
     - Ingest into `workspace/MEMORY.md` under `# Profile & Facts: User <user_id>`.
     - Ensure existing entries are updated rather than duplicated.
  2. **Personal Notes (`notes`):**
     - Extract `(id, user_id, title, content, created_at)`.
     - Generate file: `workspace/notes/user_<user_id>/note_<id>.md`.
     - Write YAML frontmatter containing `legacy_id`, `created_at`, `title`.
  3. **Reminders (`reminders`):**
     - Filter active reminders where `is_sent = 0` and `remind_at > current_time`.
     - Expired reminders (`remind_at <= current_time` and `is_sent = 0`) are logged and archived.
     - Active reminders are scheduled using OpenClaw automations CLI/JSON format.
  4. **Messages (`messages`):**
     - Conversation history is audited. Raw message dumps are NOT blindly imported into active context to prevent prompt bloat and context contamination.
     - Summary of past conversation milestones can be extracted if required.

### Phase 5: Container & Deployment Configuration
- **Objective:** Configure Dockerfile and Render Web Service specification.
- **Deliverables:**
  - `Dockerfile`: OpenClaw base image, workspace copy, entrypoint configuration.
  - `.dockerignore`: Exclude tests, local virtualenvs, git files.
  - `render.yaml`: Web service with Docker runtime, persistent disk mounted at `/data`, health check at `/health`.

### Phase 6: Cutover & Post-Migration Verification
1. Stop the legacy Python bot service on Render.
2. Trigger the new OpenClaw Docker build on Render.
3. Validate `/health` endpoint responds with HTTP 200 within 10 seconds.
4. Verify Telegram pairing or whitelist authentication with primary admin account (`5556841083`).
5. Execute end-to-end verification checklist (see Section 4).

---

## 4. Verification & Acceptance Checklist

| Step | Test Case | Target Result | Status |
|---|---|---|---|
| **V-01** | `/start` on Telegram | Welcomes user in Vietnamese, recognizes admin status | Pending |
| **V-02** | Persona & Honorifics | Address user as requested (e.g. "anh yêu") warmly | Pending |
| **V-03** | User Facts Recall | State "Anh thích đọc sách", clear, ask "Anh thích gì?" | Pending |
| **V-04** | Notes Management | Save a note, list notes, verify note file in workspace | Pending |
| **V-05** | Scheduled Reminder | Set a 1-minute reminder, assert message delivery on Telegram | Pending |
| **V-06** | Web Search & Extract | Ask live price/weather, assert table format & citation | Pending |
| **V-07** | Image Generation | `/image chú mèo phi hành gia`, assert 1024x1024 photo returned | Pending |
| **V-08** | Group Mention | Message bot in group without mention (ignored); mention (replies) | Pending |
| **V-09** | Health Check | `curl -f http://<host>:8080/health` returns HTTP 200 | Pending |
| **V-10** | Service Restart | Reboot container; verify notes, memory, and jobs persist | Pending |

---

## 5. Rollback Plan

If critical failure occurs during deployment or cutover:
1. **Trigger Rollback:** Revert Render deployment to the previous commit tag (`v2.5` or `3ecfa3e`).
2. **Restore Database:** If any data integrity issue is suspected, restore the immutable backup from `/data/legacy_backup/` to `data/airi_memory.db`.
3. **Verify Legacy Service:** Confirm the legacy Python bot resumes polling and passes health checks.
4. **Post-Mortem Analysis:** Inspect OpenClaw container logs in Render dashboard.
