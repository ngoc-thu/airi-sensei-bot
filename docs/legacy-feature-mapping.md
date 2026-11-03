# Legacy Feature Mapping: Airi Sensei v2.5 to v3.0

This document provides an exhaustive, granular mapping of every feature, component, tool, and service from Airi Sensei v2.5 to its target architecture in v3.0 on the OpenClaw Agent Runtime.

---

## 1. Telegram Interface & Bot Commands

### 1.1 `/start` Command
- **Current Implementation:** Handled in `app/bot/handlers.py:start_command`. Builds a welcome message introducing Airi Sensei, shows authorization status, and outlines the agent's capabilities.
- **Dependencies:** `python-telegram-bot`, `app/config.py`, `app/services/auth_service.py`.
- **Data Storage:** Stateless.
- **Migration Strategy:** Handled by OpenClaw's native Telegram channel greeting and onboarding message configured in `openclaw.json` and `workspace/SOUL.md`.
- **Target Implementation:** Configured via `channels.telegram.greetingMessage` or system prompt instruction upon session initiation.
- **Verification Method:** Send `/start` in Telegram chat and verify greeting text, bot persona, and authorization confirmation.

### 1.2 `/help` Command
- **Current Implementation:** Handled in `app/bot/handlers.py:help_command`. Prints examples of user facts, notes, reminders, search, link reading, art, and math.
- **Dependencies:** `python-telegram-bot`.
- **Data Storage:** Stateless.
- **Migration Strategy:** Mapped to OpenClaw system instruction in `workspace/AGENTS.md` and custom Telegram command trigger.
- **Target Implementation:** Responded natively by Airi Sensei based on the prompt catalog defined in `workspace/AGENTS.md`.
- **Verification Method:** Send `/help` in Telegram chat and assert guidance content matches expected capabilities.

### 1.3 `/auth <passcode>` Command
- **Current Implementation:** Handled in `app/bot/handlers.py:auth_command` using `AuthService.authenticate(user_id, passcode)`. Dynamically adds user ID to in-memory set.
- **Dependencies:** `app/services/auth_service.py`, `app/config.py`.
- **Data Storage:** In-memory `set` (lost on container restart), seeded from `ALLOWED_USER_IDS` in `.env`.
- **Migration Strategy:** Replaced by OpenClaw's native Channel Security model (`dmPolicy: "whitelist"` and pairing mechanism).
- **Target Implementation:** Configured in `openclaw.json` under `channels.telegram.allowedUsers` or owner pairing. No secret passcode needs to be typed in chat.
- **Verification Method:** Attempt to chat from an unlisted Telegram account (assert rejection/pairing prompt); chat from authorized account (assert successful response).

### 1.4 `/models` Command
- **Current Implementation:** Handled in `app/bot/handlers.py:models_command`. Lists active models across Groq, Gemini, OpenRouter, and B.AI tiers.
- **Dependencies:** `app/config.py`, `python-telegram-bot`.
- **Data Storage:** Stateless (reads environment configuration).
- **Migration Strategy:** Provided by OpenClaw's built-in session info or a lightweight custom command returning active model and fallbacks.
- **Target Implementation:** Agent system prompt directive or OpenClaw model status query.
- **Verification Method:** Query `/models` and verify current active model and fallback chain match `openclaw.json`.

### 1.5 `/status` Command
- **Current Implementation:** Handled in `app/bot/handlers.py:status_command`. Displays uptime, host port, auth status, active tools, and memory engine.
- **Dependencies:** `app/bot/handlers.py`, `time.time()`, `app/config.py`.
- **Data Storage:** In-memory `BOT_START_TIME`.
- **Migration Strategy:** Mapped to OpenClaw Gateway `/health` status endpoint and agent status query.
- **Target Implementation:** Telegram prompt handling or Gateway HTTP check.
- **Verification Method:** Send `/status` and confirm reporting of online status, uptime, and engine state.

### 1.6 `/clear` Command
- **Current Implementation:** Handled in `app/bot/handlers.py:clear_command`. Calls `ChatService.clear_history(user_id)` and `AiriAgent.clear_history(user_id)`.
- **Dependencies:** `app/ai/chat_service.py`, `app/agent/agent.py`, `app/services/memory_service.py`.
- **Data Storage:** SQLite `messages` table deleted for `user_id`.
- **Migration Strategy:** OpenClaw supports native session reset commands (`/reset` or `/new`).
- **Target Implementation:** OpenClaw session lifecycle management.
- **Verification Method:** Send `/clear` or `/reset`, followed by a reference to previous context; verify agent starts fresh without prior conversation context.

### 1.7 `/image` and `/taoanh` Commands
- **Current Implementation:** Handled in `app/bot/handlers.py:image_command`. Calls `ImageService.generate_image()` and sends photo via Telegram `send_photo`.
- **Dependencies:** `app/ai/image_service.py`, Pollinations AI REST endpoint.
- **Data Storage:** Temporary image buffer in memory.
- **Migration Strategy:** Mapped to `skills/airi-image/SKILL.md` tool execution within OpenClaw.
- **Target Implementation:** OpenClaw tool invocation delivering generated media directly to Telegram.
- **Verification Method:** Send `/image a futuristic cyberpunk car` and verify Telegram returns a generated 1024x1024 image.

---

## 2. Text Message Handling & Group Behavior

### 2.1 Direct Message (DM) Handling
- **Current Implementation:** `app/bot/handlers.py:text_message_handler`. Authenticates user, triggers ReAct agent, updates intermediate status messages, returns markdown answer with Agent Trace footer.
- **Dependencies:** `app/agent/agent.py`, `python-telegram-bot`.
- **Data Storage:** SQLite `messages` table.
- **Migration Strategy:** Managed directly by OpenClaw's Telegram channel dispatcher.
- **Target Implementation:** OpenClaw Agent Runtime handles incoming message, invokes ReAct loop, formats markdown, and streams/replies to user.
- **Verification Method:** Send direct text queries in Telegram and verify prompt responses.

### 2.2 Group Chat Mentions & Privacy Filter
- **Current Implementation:** `app/bot/handlers.py:text_message_handler` checks `chat_type in (GROUP, SUPERGROUP)`. Ignores messages unless mentioned (`@AiriSenseiBot`) or replying to a bot message.
- **Dependencies:** `python-telegram-bot` update metadata.
- **Data Storage:** Stateless.
- **Migration Strategy:** Native OpenClaw Telegram channel configuration:
  `groups: { "*": { requireMention: true } }`.
- **Target Implementation:** Grammatically filtered at the channel driver layer before reaching the agent.
- **Verification Method:** Add bot to a test group; verify unmentioned messages are ignored, while `@bot_username` prompts an immediate response.

### 2.3 Implicit Image Prompt Detection
- **Current Implementation:** `app/bot/handlers.py:detect_image_prompt` regex matching phrases like "vẽ cho anh...", "tạo ảnh...".
- **Dependencies:** Python `re` module.
- **Data Storage:** Stateless.
- **Migration Strategy:** Handled intelligently by OpenClaw's LLM intent classification and `generate_image` function calling in `skills/airi-image/`.
- **Target Implementation:** Natural language understanding via `skills/airi-image/SKILL.md`.
- **Verification Method:** Say "Vẽ giúp mình một chú mèo con đang ngủ" without `/image` command; verify the agent selects the image skill and generates a photo.

---

## 3. Autonomous Agent Engine & Tools

### 3.1 Web Search (`web_search`)
- **Current Implementation:** `app/agent/tools.py:web_search` using DuckDuckGo HTML scraper (`_search_ddg_sync`) with fallback to Bing HTML scraper (`_search_bing`).
- **Dependencies:** `aiohttp`, `urllib.request`, standard library.
- **Data Storage:** Stateless.
- **Migration Strategy:** Mapped to `skills/research/SKILL.md` (or OpenClaw native web search tool).
- **Target Implementation:** OpenClaw native search or custom research skill preserving clean snippet formatting and direct URLs.
- **Verification Method:** Ask "Giá vàng hôm nay" or "Thời tiết Hà Nội"; verify agent queries web and returns current data.

### 3.2 Deep Webpage Extraction (`read_webpage`)
- **Current Implementation:** `app/agent/tools.py:read_webpage` with `clean_html_to_text()` stripping scripts, styles, and tags, returning up to 2500 characters.
- **Dependencies:** `aiohttp`, `re`, `html`.
- **Data Storage:** Stateless.
- **Migration Strategy:** Integrated into `skills/research/SKILL.md` alongside search.
- **Target Implementation:** Web fetch tool executed by OpenClaw runtime with markdown conversion.
- **Verification Method:** Provide a URL to the agent and request a 3-bullet summary; verify extraction accuracy.

### 3.3 Safe Math Calculation (`calculate`)
- **Current Implementation:** `app/agent/tools.py:safe_calculate` using Python `ast.parse` to validate expressions against a strict whitelist of safe math functions (`sqrt`, `sin`, `log`, etc.).
- **Dependencies:** Python `ast`, `math`.
- **Data Storage:** Stateless.
- **Migration Strategy:** Mapped to `skills/document-generation/SKILL.md` or OpenClaw calculator tool.
- **Target Implementation:** Native calculation tool or sandboxed math evaluator.
- **Verification Method:** Request calculation: `(1250 * 45) / 1.1 + sqrt(144)`; verify exact mathematical result.

### 3.4 Local Time (`get_current_time`)
- **Current Implementation:** `app/agent/tools.py:get_vietnam_time` returning day of week and formatted date/time in GMT+7.
- **Dependencies:** Python `datetime`.
- **Data Storage:** Stateless.
- **Migration Strategy:** Built into workspace agent environment context or skill tool.
- **Target Implementation:** OpenClaw provides system timestamp or workspace time tool configured for `Asia/Ho_Chi_Minh` (GMT+7).
- **Verification Method:** Ask "Bây giờ là mấy giờ?"; verify response displays current GMT+7 time.

---

## 4. Memory & Personalization

### 4.1 User Facts (`remember_user_fact`)
- **Current Implementation:** `app/services/memory_service.py:save_fact` writing to SQLite `user_facts (user_id, key, value, updated_at)`. Injected into prompt via `get_facts_summary()`.
- **Dependencies:** `sqlite3`.
- **Data Storage:** SQLite database file `data/airi_memory.db`.
- **Migration Strategy:** Migrated via `scripts/migrate_legacy_data.py` into OpenClaw's `MEMORY.md` file and `skills/airi-user-memory/`.
- **Target Implementation:** OpenClaw memory mechanism maintaining user facts in persistent markdown / profile storage.
- **Verification Method:** State a fact: "Anh tên là Tiến, nhớ nhé"; clear context; ask "Anh tên là gì?"; verify correct retrieval.

### 4.2 Personal Notes (`manage_notes`)
- **Current Implementation:** `app/services/memory_service.py` functions: `save_note`, `get_notes`, `delete_note` backed by SQLite `notes` table.
- **Dependencies:** `sqlite3`.
- **Data Storage:** SQLite database file `data/airi_memory.db`.
- **Migration Strategy:** Migrated via `scripts/migrate_legacy_data.py` into workspace files: `workspace/notes/user_<id>/note_<note_id>.md`.
- **Target Implementation:** Handled by `skills/airi-notes/SKILL.md` allowing markdown file-based note creation, listing, searching, and deletion.
- **Verification Method:** Execute note actions: save note, list notes, delete note; verify persistence across restarts.

### 4.3 Scheduled Reminders (`set_reminder` & `reminder_worker.py`)
- **Current Implementation:** `app/services/memory_service.py:add_reminder`, `get_due_reminders`, `mark_reminder_sent`. Background polling loop in `app/services/reminder_worker.py` runs every 15 seconds.
- **Dependencies:** `asyncio`, `telegram.Bot`.
- **Data Storage:** SQLite `reminders` table.
- **Migration Strategy:** Migrated via `scripts/migrate_legacy_data.py` into OpenClaw's native automations / cron subsystem (`openclaw automations add --at ...`).
- **Target Implementation:** OpenClaw native scheduler executes one-shot or cron triggers and delivers reminders directly to the user's Telegram channel.
- **Verification Method:** Set a 1-minute reminder: "Nhắc anh uống nước sau 1 phút"; verify automated message arrives on Telegram at the designated time.

---

## 5. Model Providers & Cascading Fallback

### 5.1 Groq Cloud Tier
- **Current Implementation:** `AsyncOpenAI` client pointing to `https://api.groq.com/openai/v1` with `GROQ_API_KEY`. Models: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`.
- **Target Implementation:** Configured as primary provider in `openclaw.json` (`groq/llama-3.3-70b-versatile` or custom Groq endpoint).

### 5.2 Google Gemini Tier
- **Current Implementation:** `AsyncOpenAI` client pointing to `https://generativelanguage.googleapis.com/v1beta/openai/` with `GEMINI_API_KEY`. Models: `gemini-3.5-flash`, `gemini-2.5-flash`.
- **Target Implementation:** Configured as secondary fallback provider in `openclaw.json` (`google/gemini-2.5-flash` or OpenAI-compatible endpoint).

### 5.3 OpenRouter Free Tier
- **Current Implementation:** `AsyncOpenAI` client pointing to `https://openrouter.ai/api/v1` with `OPENROUTER_API_KEY`. Models: `nvidia/nemotron-3.5-lightning:free`, `google/gemma-4-31b-it:free`.
- **Target Implementation:** Configured as tertiary fallback provider in `openclaw.json`.

### 5.4 Zero-Failure Fallback
- **Current Implementation:** Pollinations `openai-fast` (`https://text.pollinations.ai/openai`) with zero API key requirement.
- **Target Implementation:** Documented in `docs/model-providers.md` as emergency fallback.

---

## 6. HTTP Server & Health Checks

### 6.1 Port & Endpoint Binding
- **Current Implementation:** `app/server/web.py` using `aiohttp` listening on `$PORT` (default 8080) and `$HOST` (0.0.0.0). Routes: `/` (HTML banner) and `/health` (JSON uptime).
- **Dependencies:** `aiohttp`.
- **Data Storage:** In-memory `SERVER_START_TIME`.
- **Migration Strategy:** OpenClaw Gateway native HTTP server binds to `$PORT` and serves `/health`.
- **Target Implementation:** OpenClaw Gateway HTTP control plane.
- **Verification Method:** Perform `curl -f http://localhost:8080/health` and verify HTTP 200 response with status `ok`.
