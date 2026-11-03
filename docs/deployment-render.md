# Render Production Deployment Guide: Airi Sensei v3.0

## 1. Architecture & Service Overview

Airi Sensei v3.0 runs as a containerized **Web Service** on **Render**. 

OpenClaw Gateway acts as the unified daemon executing:
1. The native Telegram long-polling driver.
2. The agent execution and tool sandboxing loop.
3. The HTTP health check and management server on the assigned Render `$PORT`.

```
                    ┌───────────────────────────────────────────────┐
                    │               Render Cloud                     │
                    │                                               │
Telegram Webhook/   │   ┌────────────────────────────────────────┐  │
Polling Traffic ───┼──>│ Web Service: airi-sensei-bot           │  │
                    │   │ - Runtime: Docker                      │  │
                    │   │ - Plan: Starter ($7/mo)                │  │
                    │   │ - Port: $PORT (8080)                   │  │
                    │   │ - Health Check: /health                │  │
                    │   └───────────────────┬────────────────────┘  │
                    │                       │                       │
                    │                       ▼ Mount: /data          │
                    │   ┌────────────────────────────────────────┐  │
                    │   │ Persistent Disk (1GB+ SSD)             │  │
                    │   │ - /data/.openclaw/                     │  │
                    │   │ - /data/workspace/                     │  │
                    │   │ - /data/legacy_backup/                 │  │
                    │   └────────────────────────────────────────┘  │
                    └───────────────────────────────────────────────┘
```

---

## 2. Infrastructure Requirements & Sizing

### 2.1 Instance Sizing
- **Recommended Plan:** Render **Starter Plan** ($7/month).
- **CPU / RAM:** 0.5 CPU, 512MB RAM (sufficient for OpenClaw Gateway without Chromium).
- **Persistent Disk:** 1 GB (Render Disk Add-on, mounted at `/data`).

> [!IMPORTANT]
> **Free Tier Limitations:**
> Render's Free tier does **not** support Persistent Disks. Containers on the Free tier run on ephemeral filesystems that wipe all disk contents when sleeping or restarting. Furthermore, Free tier instances sleep after 15 minutes of inactivity. For continuous 24/7 Telegram operation with persistent memory and notes, the **Starter Plan** is mandatory.

---

## 3. Environment Variables Specification

Configure the following variables in the Render Dashboard (`Environment` tab):

| Variable Name | Required | Default / Example | Purpose |
|---|---|---|---|
| `PORT` | Auto (Render) | `8080` | Service port exposed to the internet & health check |
| `OPENCLAW_CONFIG_PATH` | Yes | `/data/.openclaw/openclaw.json` | Explicit path to OpenClaw runtime config |
| `OPENCLAW_HOME` | Yes | `/data/.openclaw` | Root directory for state, sessions, and SQLite stores |
| `OPENCLAW_GATEWAY_TOKEN` | Yes | `(Generated secret token)` | Bearer token securing the Gateway control plane |
| `TELEGRAM_BOT_TOKEN` | Yes | `(Token from @BotFather)` | Telegram Bot API token |
| `GROQ_API_KEY` | Optional | `gsk_...` | API Key for Tier 1 inference (Groq Cloud) |
| `GEMINI_API_KEY` | Optional | `AIza...` | API Key for Tier 2 inference (Google Gemini) |
| `OPENROUTER_API_KEY` | Optional | `sk-or-v1-...` | API Key for Tier 3 inference (OpenRouter Free Tier) |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 4. Docker Container Configuration

### 4.1 Base Image & Pinned Version
OpenClaw is pinned to a stable, reproducible release tag from the GitHub Container Registry:
- **Image:** `ghcr.io/openclaw/openclaw:2026.10.10-beta.5-slim` (or verified stable equivalent).
- **Variant:** `slim` (minimizes image size, avoids heavy Chromium dependencies since browser automation is deferred).

### 4.2 Multi-Stage / Wrapper Dockerfile
The deployment Dockerfile mounts the persistent volume at runtime and executes a bootstrap script to:
1. Verify `/data` directory structure (`/data/.openclaw`, `/data/workspace`, `/data/legacy_backup`).
2. Scaffold default instruction files (`AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`) and skills if not already present on disk.
3. Launch the OpenClaw Gateway bound to `0.0.0.0` and Render's `$PORT`.

### 4.3 Health Check Endpoint
Render sends HTTP GET requests to `/health`.
OpenClaw Gateway provides `/health` natively, returning:
```json
{
  "status": "ok",
  "version": "3.0.0",
  "channels": {
    "telegram": "connected"
  }
}
```

---

## 5. Persistent Volume Mount (`/data`)

Render provisions the persistent disk to `/data`. The layout inside `/data` is strictly isolated:

```
/data/
├── .openclaw/
│   ├── openclaw.json       <-- Runtime configuration
│   ├── identity.json       <-- Generated gateway keys
│   └── sessions/           <-- Active user session DBs
├── workspace/
│   ├── AGENTS.md           <-- Airi persona & instructions
│   ├── SOUL.md             <-- Personality definitions
│   ├── USER.md             <-- User profile defaults
│   ├── TOOLS.md            <-- Tool constraints
│   ├── MEMORY.md           <-- Persistent user facts
│   ├── notes/              <-- Personal notes per user
│   └── skills/             <-- Airi modular skills
└── legacy_backup/          <-- Archived SQLite databases
```

---

## 6. Process Lifecycle & Graceful Shutdown

1. **Startup:**
   - Container initializes.
   - Entrypoint validates volume permissions on `/data`.
   - OpenClaw Gateway starts HTTP server on `$PORT` first to immediately satisfy Render's health checks.
   - Telegram long-polling starts asynchronously.
2. **Rolling Deploys:**
   - Render spins up the new container instance while old instance is still receiving traffic.
   - When the new container's `/health` returns 200, Render terminates the old container with `SIGTERM`.
   - To prevent Telegram polling conflicts, the entrypoint acquires an exclusive lock file on `/data/.openclaw/telegram.lock` with a 15-second grace period for the old container to cleanly shut down.
3. **Shutdown (`SIGTERM` / `SIGINT`):**
   - OpenClaw catches the signal, stops accepting new Telegram updates, flushes in-flight memory writes to SQLite, closes database handles, and exits with code 0 within 10 seconds.
