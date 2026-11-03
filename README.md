# 🌸 Airi Sensei Telegram Bot v3.0 (@AiriSenseiBot)

> **Next-Generation Autonomous AI Agent:** Built on **OpenClaw Agent Runtime** + **Airi Personalized Persona Layer**. Featuring multi-tier LLM fallback (Groq 120B / Gemini Flash / OpenRouter), deep real-time research, Flux 1024x1024 AI art, persistent long-term memory, personal notes, and native automations — deployed 24/7 on Render (Docker Web Service, Starter Plan $7/mo).

---

## 🌟 Architecture Highlights (v3.0)

1. 🤖 **OpenClaw Primary Agent Runtime:**
   - Single-owner Telegram channel driver powered by grammY long-polling.
   - Autonomous ReAct thought-action-observation loop with tool sandboxing.
   - Native automations and cron scheduling for exact time reminders.
   - Strict workspace filesystem isolation (`/data/workspace`).

2. 🌸 **Airi Sensei Personality Layer:**
   - Deep conversational empathy, warm Vietnamese fluency, and lively expressions.
   - **Dynamic Honorific Adaptation:** Readily accepts user-requested address (*anh yêu*, *chồng*, *sếp*).
   - Strict research protocol: DuckDuckGo search + deep webpage extraction (`read_webpage`) for verified commodity prices, gold rates, and currency tables with source citations.

3. ⚡ **Multi-Tier Cascading Fallback:**
   - **Tier 1:** Groq Cloud Flagship (`openai/gpt-oss-120b`, ultra-fast 500 T/s).
   - **Tier 2:** Google Gemini (`gemini-2.5-flash`, 1M context capacity).
   - **Tier 3:** OpenRouter Free Tier (`google/gemma-4-31b-it:free`, `nvidia/nemotron-3.5-lightning:free`).
   - **Tier 4:** Zero-Failure Emergency Fallback (`openai-fast`).

4. 🎨 **AI Art Studio (`skills/airi-image/`):**
   - Commands: `/image <prompt>` or `/taoanh <prompt>`, plus automatic natural conversation detection.
   - Automatic prompt cleaning, Vietnamese-to-English enhancement, and Flux 1024x1024 generation (with Turbo fallback).

5. 💾 **100% Data Preservation & Migration:**
   - Dedicated scripts for atomic backup (`scripts/backup_legacy_db.py`) and idempotent migration (`scripts/migrate_legacy_data.py`).
   - User facts migrated to `MEMORY.md`, notes to Markdown files, active reminders to OpenClaw automations.

---

## 📋 Commands on Telegram

| Command | Description |
|---|---|
| `/start` | Welcome greeting, capability overview, and authorization status |
| `/help` | Detailed usage guide and example prompts |
| `/image <prompt>` | Generate 1024x1024 artwork using Flux |
| `/taoanh <prompt>` | Vietnamese alias for `/image` |
| `/models` | View active LLM tiers and fallback configuration |
| `/status` | View system health, uptime, and active skills |
| `/clear` | Refresh conversation context to start a new topic |
| *Natural message* | Chat, ask for research, calculate math, save notes, or schedule reminders |

---

## 🛠️ Modular Skills Directory

```
skills/
├── airi-image/            # Pollinations Flux/Turbo 1024x1024 generation
├── airi-notes/            # Markdown personal notes management
├── airi-user-memory/      # Persistent facts & profile in MEMORY.md
├── airi-reminders/        # Automated scheduled reminders
├── research/              # DuckDuckGo search + deep webpage extraction
└── document-generation/   # Sandboxed AST calculation & markdown tables
```

---

## 🚀 Deployment to Render (Docker Web Service)

1. **Prerequisites:**
   - Render Account with **Starter Plan** ($7/mo) to support persistent disks.
   - Telegram Bot Token from `@BotFather`.
   - API keys for Groq, Gemini, and OpenRouter (optional).

2. **Deploy via `render.yaml`:**
   - Connect your GitHub repository to Render.
   - Render automatically provisions the Docker container, attaches the 1 GB persistent disk at `/data`, and configures the `/health` endpoint.

3. **Required Environment Variables:**
   - `OPENCLAW_GATEWAY_TOKEN`: Secure random token securing the gateway.
   - `TELEGRAM_BOT_TOKEN`: Telegram bot token.
   - `ALLOWED_USER_IDS`: Comma-separated list of authorized Telegram user IDs.
   - `GROQ_API_KEY`: API key for Groq Cloud.
   - `GEMINI_API_KEY`: API key for Google Gemini.
   - `OPENROUTER_API_KEY`: API key for OpenRouter.

---

## 📚 Technical Documentation

- [v3.0 Architecture Specification](docs/architecture-v3.md)
- [Legacy Feature Mapping (v2.5 to v3.0)](docs/legacy-feature-mapping.md)
- [Migration Plan & Runbook](docs/migration-plan.md)
- [Model Provider & Fallback Details](docs/model-providers.md)
- [Data Migration Manual](docs/data-migration.md)
- [Security Review & Tool Sandboxing](docs/security-review.md)
- [Render Deployment Guide](docs/deployment-render.md)
