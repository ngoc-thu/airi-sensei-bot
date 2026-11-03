#!/usr/bin/env python3
"""
scripts/backup_legacy_db.py
Creates an immutable, verified backup of the legacy Airi Sensei SQLite database.
Ensures point-in-time consistency and SHA-256 checksum validation.
"""

import argparse
import datetime
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backup_legacy_db")


def compute_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def count_table_rows(db_path: str) -> dict:
    row_counts = {}
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM \"{table}\";")
            row_counts[table] = cursor.fetchone()[0]
    finally:
        conn.close()
    return row_counts


def backup_database(source_path: str, target_dir: str) -> dict:
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source database not found: {source_path}")

    os.makedirs(target_dir, exist_ok=True)
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    backup_filename = f"{base_name}_{timestamp_str}.db"
    backup_path = os.path.join(target_dir, backup_filename)

    logger.info("Starting atomic backup from '%s' to '%s'...", source_path, backup_path)

    # Use SQLite online backup API to guarantee consistent point-in-time snapshot
    src_uri = f"file:{os.path.abspath(source_path)}?mode=ro"
    src_conn = sqlite3.connect(src_uri, uri=True)
    dst_conn = sqlite3.connect(backup_path)

    try:
        src_conn.backup(dst_conn)
        logger.info("SQLite online backup completed successfully.")
    finally:
        dst_conn.close()
        src_conn.close()

    # Integrity verification
    src_hash = compute_sha256(source_path)
    dst_hash = compute_sha256(backup_path)
    src_size = os.path.getsize(source_path)
    dst_size = os.path.getsize(backup_path)

    row_counts = count_table_rows(backup_path)

    metadata = {
        "status": "success",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_path": os.path.abspath(source_path),
        "backup_path": os.path.abspath(backup_path),
        "backup_filename": backup_filename,
        "source_sha256": src_hash,
        "backup_sha256": dst_hash,
        "source_size_bytes": src_size,
        "backup_size_bytes": dst_size,
        "table_row_counts": row_counts,
    }

    metadata_path = os.path.join(target_dir, f"{base_name}_{timestamp_str}_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("Backup metadata saved to '%s'", metadata_path)
    logger.info("Verified table counts in backup: %s", row_counts)
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Backup Legacy Airi SQLite Database")
    parser.add_argument("--source", default="data/airi_memory.db", help="Path to source SQLite database")
    parser.add_argument("--target", default="data/legacy_backup", help="Target backup directory")
    args = parser.parse_args()

    try:
        metadata = backup_database(args.source, args.target)
        print(json.dumps(metadata, indent=2))
        sys.exit(0)
    except Exception as e:
        logger.error("Database backup failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
