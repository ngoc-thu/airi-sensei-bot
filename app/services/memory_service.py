import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Dịch vụ lưu trữ trí nhớ dài hạn bền vững (Persistent Long-Term Memory) qua SQLite
    theo chuẩn OpenClaw Assistant:
    - Lưu lịch sử hội thoại xuyên suốt mọi lần khởi động lại server.
    - Lưu hồ sơ cá nhân và sở thích của người dùng (user_facts).
    - Lưu sổ tay ghi chú (notes).
    - Lưu lịch nhắc nhở tự động (reminders).
    """

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            db_path = os.environ.get("AIRI_DB_PATH", "/tmp/airi_memory.db")
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                logger.warning("Could not create db directory %s: %s", db_dir, e)
                self.db_path = "/tmp/airi_memory.db"
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path)
        except Exception as e:
            logger.warning("Could not connect to %s: %s, using :memory:", self.db_path, e)
            self.db_path = ":memory:"
            conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
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
                    CREATE TABLE IF NOT EXISTS user_facts (
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
                    CREATE TABLE IF NOT EXISTS notes (
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
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        reminder_text TEXT NOT NULL,
                        remind_at REAL NOT NULL,
                        is_sent INTEGER DEFAULT 0,
                        created_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id, id DESC)"
                )
                conn.commit()
        except Exception as e:
            logger.error("Error initializing DB at %s: %s", self.db_path, e)

    # --- Lịch sử hội thoại ---
    def add_message(self, user_id: int, role: str, content: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, content, time.time()),
            )
            conn.commit()

    def get_history(self, user_id: int, limit: int = 14) -> List[Dict[str, str]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
            rows = cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def clear_history(self, user_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            conn.commit()

    # --- Hồ sơ & Sự thật về người dùng (Facts) ---
    def save_fact(self, user_id: int, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_facts (user_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (user_id, key, value, time.time()),
            )
            conn.commit()

    def get_facts(self, user_id: int) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT key, value FROM user_facts WHERE user_id = ?",
                (user_id,),
            )
            rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

    def get_facts_summary(self, user_id: int) -> str:
        facts = self.get_facts(user_id)
        if not facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in facts.items()]
        return "Thông tin cá nhân đã ghi nhớ về người dùng:\n" + "\n".join(lines)

    # --- Ghi chú cá nhân (Notes) ---
    def save_note(self, user_id: int, title: str, content: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO notes (user_id, title, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, title, content, time.time()),
            )
            conn.commit()
            return cursor.lastrowid

    def get_notes(self, user_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, content, created_at FROM notes WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def delete_note(self, user_id: int, note_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM notes WHERE user_id = ? AND id = ?",
                (user_id, note_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    # --- Lập lịch nhắc nhở (Reminders) ---
    def add_reminder(self, user_id: int, reminder_text: str, remind_at: float) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reminders (user_id, reminder_text, remind_at, is_sent, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (user_id, reminder_text, remind_at, time.time()),
            )
            conn.commit()
            return cursor.lastrowid

    def get_due_reminders(self) -> List[Dict[str, Any]]:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, user_id, reminder_text, remind_at FROM reminders WHERE is_sent = 0 AND remind_at <= ?",
                (now,),
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def mark_reminder_sent(self, reminder_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
            conn.commit()

    def get_pending_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, reminder_text, remind_at FROM reminders
                WHERE user_id = ? AND is_sent = 0
                ORDER BY remind_at ASC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]
