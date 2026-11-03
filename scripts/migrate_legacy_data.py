#!/usr/bin/env python3
"""
scripts/migrate_legacy_data.py
Idempotent migration utility from Airi Sensei v2.5 SQLite database to OpenClaw v3.0 workspace.
Preserves user facts, notes, reminders, and archives legacy messages safely.
"""

import argparse
import datetime
import json
import logging
import os
import re
import sqlite3
import sys
import time
from typing import Any, Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("migrate_legacy_data")


def format_timestamp(ts: float) -> str:
    try:
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()
    except Exception:
        return str(ts)


def migrate_user_facts(conn: sqlite3.Connection, workspace_dir: str, dry_run: bool = False) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, key, value, updated_at FROM user_facts ORDER BY user_id, key;")
    facts = cursor.fetchall()
    if not facts:
        logger.info("No user facts found to migrate.")
        return 0

    memory_path = os.path.join(workspace_dir, "MEMORY.md")
    os.makedirs(workspace_dir, exist_ok=True)

    existing_content = ""
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
    else:
        existing_content = "# Airi Sensei Long-Term Memory (MEMORY.md)\n\n"

    # Group facts by user_id
    users_facts: Dict[int, List[Tuple[str, str, float]]] = {}
    for uid, key, val, upd in facts:
        users_facts.setdefault(uid, []).append((key, val, upd))

    updated_content = existing_content
    for uid, user_fact_list in users_facts.items():
        user_header = f"## User Profile & Facts (User ID: {uid})"
        if user_header not in updated_content:
            user_block = f"\n\n{user_header}\n"
            for k, v, upd in user_fact_list:
                user_block += f"- **{k}**: {v} *(Updated: {format_timestamp(upd)})*\n"
            updated_content += user_block
        else:
            # Update facts inside existing user section
            for k, v, upd in user_fact_list:
                pattern = rf"- \*\*{re.escape(k)}\*\*:.*"
                replacement = f"- **{k}**: {v} *(Updated: {format_timestamp(upd)})*"
                if re.search(pattern, updated_content):
                    updated_content = re.sub(pattern, replacement, updated_content)
                else:
                    # Append under the header
                    idx = updated_content.find(user_header) + len(user_header)
                    updated_content = (
                        updated_content[:idx] + f"\n{replacement}" + updated_content[idx:]
                    )

    if not dry_run:
        with open(memory_path, "w", encoding="utf-8") as f:
            f.write(updated_content.strip() + "\n")
        logger.info("Migrated %d user facts into '%s'", len(facts), memory_path)
    else:
        logger.info("[DRY-RUN] Would migrate %d user facts into '%s'", len(facts), memory_path)

    return len(facts)


def migrate_notes(conn: sqlite3.Connection, workspace_dir: str, dry_run: bool = False) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, title, content, created_at FROM notes ORDER BY id ASC;")
    notes = cursor.fetchall()
    if not notes:
        logger.info("No notes found to migrate.")
        return 0

    count = 0
    for nid, uid, title, content, created_at in notes:
        user_notes_dir = os.path.join(workspace_dir, "notes", f"user_{uid}")
        if not dry_run:
            os.makedirs(user_notes_dir, exist_ok=True)

        note_file = os.path.join(user_notes_dir, f"note_{nid}.md")
        note_text = (
            f"---\n"
            f"legacy_id: {nid}\n"
            f"user_id: {uid}\n"
            f"title: \"{title}\"\n"
            f"created_at_utc: \"{format_timestamp(created_at)}\"\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"{content}\n"
        )
        if not dry_run:
            with open(note_file, "w", encoding="utf-8") as f:
                f.write(note_text)
        count += 1

    if not dry_run:
        logger.info("Migrated %d notes into '%s/notes/'", count, workspace_dir)
    else:
        logger.info("[DRY-RUN] Would migrate %d notes into '%s/notes/'", count, workspace_dir)

    return count


def migrate_reminders(conn: sqlite3.Connection, workspace_dir: str, dry_run: bool = False) -> Dict[str, int]:
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, reminder_text, remind_at, is_sent, created_at FROM reminders ORDER BY id ASC;")
    reminders = cursor.fetchall()

    now = time.time()
    active_jobs: List[Dict[str, Any]] = []
    archived_jobs: List[Dict[str, Any]] = []

    for rid, uid, text, remind_at, is_sent, created_at in reminders:
        record = {
            "id": f"legacy_reminder_{rid}",
            "legacy_id": rid,
            "user_id": uid,
            "message": text,
            "scheduled_at_timestamp": remind_at,
            "scheduled_at_iso": format_timestamp(remind_at),
            "created_at_iso": format_timestamp(created_at),
            "timezone": "Asia/Ho_Chi_Minh",
        }
        if is_sent == 1:
            record["status"] = "delivered"
            archived_jobs.append(record)
        elif remind_at <= now:
            record["status"] = "expired"
            archived_jobs.append(record)
        else:
            record["status"] = "pending"
            record["action"] = {
                "channel": "telegram",
                "recipient": str(uid),
                "text": f"⏰ **Airi nhắc nhở anh nè:**\n\n_{text}_\n\n— Airi Sensei 🌸",
            }
            active_jobs.append(record)

    automations_dir = os.path.join(workspace_dir, "automations")
    if not dry_run:
        os.makedirs(automations_dir, exist_ok=True)
        reminders_file = os.path.join(automations_dir, "reminders.json")
        archived_file = os.path.join(automations_dir, "archived_reminders.json")

        with open(reminders_file, "w", encoding="utf-8") as f:
            json.dump(active_jobs, f, indent=2, ensure_ascii=False)

        with open(archived_file, "w", encoding="utf-8") as f:
            json.dump(archived_jobs, f, indent=2, ensure_ascii=False)

        logger.info(
            "Migrated reminders: %d active into '%s', %d archived into '%s'",
            len(active_jobs),
            reminders_file,
            len(archived_jobs),
            archived_file,
        )
    else:
        logger.info(
            "[DRY-RUN] Would migrate reminders: %d active, %d archived",
            len(active_jobs),
            len(archived_jobs),
        )

    return {"active": len(active_jobs), "archived": len(archived_jobs)}


def migrate_messages_audit(conn: sqlite3.Connection, workspace_dir: str, dry_run: bool = False) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM messages;")
    total, min_ts, max_ts = cursor.fetchone()
    if not total:
        return {"total_messages": 0}

    cursor.execute("SELECT DISTINCT user_id FROM messages;")
    user_ids = [row[0] for row in cursor.fetchall()]

    audit = {
        "status": "archived_audit",
        "description": (
            "Legacy conversation messages are preserved in immutable backup "
            "and excluded from active context to maintain low token latency."
        ),
        "total_messages": total,
        "earliest_timestamp_utc": format_timestamp(min_ts) if min_ts else None,
        "latest_timestamp_utc": format_timestamp(max_ts) if max_ts else None,
        "active_users": user_ids,
    }

    if not dry_run:
        archive_dir = os.path.join(workspace_dir, "memory")
        os.makedirs(archive_dir, exist_ok=True)
        audit_file = os.path.join(archive_dir, "legacy_conversations_summary.json")
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2, ensure_ascii=False)
        logger.info("Saved legacy messages audit to '%s'", audit_file)

    return audit


def run_migration(db_path: str, workspace_dir: str, dry_run: bool = False) -> Dict[str, Any]:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at '{db_path}'")

    logger.info("Opening database '%s' in read-only mode...", db_path)
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)

    try:
        facts_count = migrate_user_facts(conn, workspace_dir, dry_run=dry_run)
        notes_count = migrate_notes(conn, workspace_dir, dry_run=dry_run)
        reminders_res = migrate_reminders(conn, workspace_dir, dry_run=dry_run)
        messages_res = migrate_messages_audit(conn, workspace_dir, dry_run=dry_run)

        report = {
            "status": "success",
            "dry_run": dry_run,
            "database": os.path.abspath(db_path),
            "workspace": os.path.abspath(workspace_dir),
            "migrated": {
                "user_facts": facts_count,
                "notes": notes_count,
                "reminders_active": reminders_res["active"],
                "reminders_archived": reminders_res["archived"],
                "messages_audited": messages_res.get("total_messages", 0),
            },
        }
        return report
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate Legacy SQLite Data to OpenClaw Workspace")
    parser.add_argument("--db-path", default="data/airi_memory.db", help="Path to legacy SQLite database")
    parser.add_argument("--workspace", default="workspace", help="Path to OpenClaw workspace directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run without modifying files")
    args = parser.parse_args()

    try:
        report = run_migration(args.db_path, args.workspace, dry_run=args.dry_run)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        logger.error("Migration failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
