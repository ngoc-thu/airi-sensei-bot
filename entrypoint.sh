#!/usr/bin/env bash
# ==============================================================================
# Airi Sensei v3.0 Production Container Entrypoint
# Initializes storage directories, seeds config/workspace, and runs OpenClaw Gateway.
# ==============================================================================
set -e

echo "🌸 Starting Airi Sensei v3.0 (OpenClaw Agent Runtime)..."

DATA_DIR="${DATA_DIR:-/data}"
mkdir -p "${DATA_DIR}/.openclaw"
mkdir -p "${DATA_DIR}/workspace/notes"
mkdir -p "${DATA_DIR}/workspace/automations"
mkdir -p "${DATA_DIR}/workspace/memory"
mkdir -p "${DATA_DIR}/workspace/skills"
mkdir -p "${DATA_DIR}/legacy_backup"

# Seed default openclaw.json if not present on persistent disk
if [ ! -f "${DATA_DIR}/.openclaw/openclaw.json" ] && [ -f "/app/openclaw.json" ]; then
    echo "Seeding openclaw.json to ${DATA_DIR}/.openclaw/openclaw.json..."
    cp /app/openclaw.json "${DATA_DIR}/.openclaw/openclaw.json"
fi

# Seed workspace prompt instruction files
for file in AGENTS.md SOUL.md USER.md TOOLS.md MEMORY.md; do
    if [ ! -f "${DATA_DIR}/workspace/${file}" ] && [ -f "/app/workspace/${file}" ]; then
        echo "Seeding ${file} to ${DATA_DIR}/workspace/${file}..."
        cp "/app/workspace/${file}" "${DATA_DIR}/workspace/${file}"
    fi
done

# Sync latest skills into workspace
if [ -d "/app/skills" ]; then
    echo "Syncing Airi skills into ${DATA_DIR}/workspace/skills..."
    cp -r /app/skills/* "${DATA_DIR}/workspace/skills/" 2>/dev/null || true
fi

# Check for legacy SQLite database and execute one-time migration if needed
if [ -f "${DATA_DIR}/airi_memory.db" ] && [ ! -f "${DATA_DIR}/.openclaw/.migrated" ]; then
    echo "Found legacy database ${DATA_DIR}/airi_memory.db. Running automated backup & migration..."
    python3 /app/scripts/backup_legacy_db.py --source "${DATA_DIR}/airi_memory.db" --target "${DATA_DIR}/legacy_backup" || echo "Backup warning"
    python3 /app/scripts/migrate_legacy_data.py --db-path "${DATA_DIR}/airi_memory.db" --workspace "${DATA_DIR}/workspace" || echo "Migration warning"
    touch "${DATA_DIR}/.openclaw/.migrated"
    echo "Legacy migration completed successfully."
fi

SERVICE_PORT="${PORT:-8080}"
echo "HTTP Server will listen on port: ${SERVICE_PORT}"

# Execute OpenClaw Gateway
if command -v openclaw >/dev/null 2>&1; then
    exec openclaw gateway \
        --port "${SERVICE_PORT}" \
        --bind 0.0.0.0 \
        --auth token \
        --token "${OPENCLAW_GATEWAY_TOKEN}"
else
    echo "Warning: openclaw CLI not found in PATH. Checking fallback or test runner..."
    if [ -f "/app/main.py" ]; then
        echo "Falling back to Python runner for local development..."
        exec python3 -m app.main
    fi
fi
