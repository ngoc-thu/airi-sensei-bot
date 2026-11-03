import json
import os
import sqlite3
import tempfile
import time
import pytest
from scripts.backup_legacy_db import backup_database, compute_sha256, count_table_rows
from scripts.migrate_legacy_data import (
    run_migration,
    migrate_user_facts,
    migrate_notes,
    migrate_reminders,
    migrate_messages_audit,
)


@pytest.fixture
def sample_legacy_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE user_facts (
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (user_id, key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reminder_text TEXT NOT NULL,
                remind_at REAL NOT NULL,
                is_sent INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
            """
        )

        now = time.time()
        # Insert sample data
        conn.execute(
            "INSERT INTO messages (user_id, role, content, timestamp) VALUES (123, 'user', 'Hello', ?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO user_facts (user_id, key, value, updated_at) VALUES (123, 'ten_goi', 'Tien', ?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO notes (user_id, title, content, created_at) VALUES (123, 'Ke hoach', 'Hoc OpenClaw', ?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO reminders (user_id, reminder_text, remind_at, is_sent, created_at) "
            "VALUES (123, 'Hop', ?, 0, ?)",
            (now + 3600, now),
        )
        conn.execute(
            "INSERT INTO reminders (user_id, reminder_text, remind_at, is_sent, created_at) "
            "VALUES (123, 'Choi', ?, 0, ?)",
            (now - 3600, now),
        )
        conn.execute(
            "INSERT INTO reminders (user_id, reminder_text, remind_at, is_sent, created_at) "
            "VALUES (123, 'Uong', ?, 1, ?)",
            (now - 7200, now),
        )
        conn.commit()
    finally:
        conn.close()

    yield db_path

    if os.path.exists(db_path):
        os.remove(db_path)


def test_backup_database_creates_valid_snapshot(sample_legacy_db):
    with tempfile.TemporaryDirectory() as target_dir:
        metadata = backup_database(sample_legacy_db, target_dir)
        assert metadata["status"] == "success"
        assert os.path.exists(metadata["backup_path"])
        assert metadata["source_size_bytes"] > 0
        assert metadata["table_row_counts"]["messages"] == 1
        assert metadata["table_row_counts"]["user_facts"] == 1
        assert metadata["table_row_counts"]["notes"] == 1
        assert metadata["table_row_counts"]["reminders"] == 3


def test_migrate_user_facts_idempotence(sample_legacy_db):
    with tempfile.TemporaryDirectory() as workspace_dir:
        conn = sqlite3.connect(sample_legacy_db)
        try:
            # First migration pass
            count = migrate_user_facts(conn, workspace_dir)
            assert count == 1

            memory_path = os.path.join(workspace_dir, "MEMORY.md")
            assert os.path.exists(memory_path)
            with open(memory_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "ten_goi" in content
            assert "Tien" in content

            # Update fact in database
            now = time.time()
            conn.execute(
                "UPDATE user_facts SET value = 'Nguyen Ngoc Tien', updated_at = ? WHERE key = 'ten_goi'",
                (now,),
            )
            conn.commit()

            # Second migration pass (idempotent update)
            count2 = migrate_user_facts(conn, workspace_dir)
            assert count2 == 1

            with open(memory_path, "r", encoding="utf-8") as f:
                updated_content = f.read()

            assert "Nguyen Ngoc Tien" in updated_content
            # Ensure no duplicate bullet lines
            assert updated_content.count("- **ten_goi**:") == 1
        finally:
            conn.close()


def test_migrate_notes(sample_legacy_db):
    with tempfile.TemporaryDirectory() as workspace_dir:
        conn = sqlite3.connect(sample_legacy_db)
        try:
            count = migrate_notes(conn, workspace_dir)
            assert count == 1

            note_file = os.path.join(workspace_dir, "notes", "user_123", "note_1.md")
            assert os.path.exists(note_file)
            with open(note_file, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Ke hoach" in content
            assert "Hoc OpenClaw" in content
        finally:
            conn.close()


def test_migrate_reminders_active_and_expired(sample_legacy_db):
    with tempfile.TemporaryDirectory() as workspace_dir:
        conn = sqlite3.connect(sample_legacy_db)
        try:
            res = migrate_reminders(conn, workspace_dir)
            assert res["active"] == 1  # 'Hop online' is in the future
            assert res["archived"] == 2  # 'Di choi' (expired) + 'Uong thuoc' (is_sent=1)

            reminders_file = os.path.join(workspace_dir, "automations", "reminders.json")
            archived_file = os.path.join(workspace_dir, "automations", "archived_reminders.json")

            assert os.path.exists(reminders_file)
            assert os.path.exists(archived_file)

            with open(reminders_file, "r", encoding="utf-8") as f:
                active_list = json.load(f)
            assert len(active_list) == 1
            assert active_list[0]["message"] == "Hop"
            assert active_list[0]["status"] == "pending"

            with open(archived_file, "r", encoding="utf-8") as f:
                archived_list = json.load(f)
            assert len(archived_list) == 2
        finally:
            conn.close()


def test_migrate_messages_audit(sample_legacy_db):
    with tempfile.TemporaryDirectory() as workspace_dir:
        conn = sqlite3.connect(sample_legacy_db)
        try:
            audit = migrate_messages_audit(conn, workspace_dir)
            assert audit["total_messages"] == 1
            assert 123 in audit["active_users"]

            summary_file = os.path.join(workspace_dir, "memory", "legacy_conversations_summary.json")
            assert os.path.exists(summary_file)
        finally:
            conn.close()


def test_run_migration_full(sample_legacy_db):
    with tempfile.TemporaryDirectory() as workspace_dir:
        report = run_migration(sample_legacy_db, workspace_dir, dry_run=False)
        assert report["status"] == "success"
        assert report["migrated"]["user_facts"] == 1
        assert report["migrated"]["notes"] == 1
        assert report["migrated"]["reminders_active"] == 1
        assert report["migrated"]["reminders_archived"] == 2
        assert report["migrated"]["messages_audited"] == 1
