# Airi Sensei v3.0 Security Review & Tool Sandboxing Specification

## 1. Threat Model & Security Posture

Airi Sensei v3.0 operates as an autonomous agent in direct communication with external Telegram users and external web endpoints. The threat model addresses four primary vectors:
1. **Prompt Injection & Persona Jailbreaking:** Attackers attempting to force the agent to reveal secrets, bypass restrictions, or adopt unauthorized personas.
2. **Unauthorized Access & Telegram Impersonation:** Unauthenticated users attempting to command the bot or execute tools.
3. **Remote Code Execution (RCE) via Tools:** Exploitation of tool inputs (e.g. math calculator, shell commands, file path traversal).
4. **Data Exfiltration:** Malicious attempts to read environment variables, API keys, or private files outside the workspace.

---

## 2. Hard Security Controls Implemented

### 2.1 Tool Allowlist & Explicit Denylist
The OpenClaw runtime enforces an explicit capability whitelist:
- **Allowed Tools:**
  - `web_search`: Network egress restricted to search engine GET requests.
  - `read_webpage`: Network egress restricted to HTTP/HTTPS document retrieval with 2500-char truncation.
  - `calculate`: Pure Python AST math evaluator with zero access to `__builtins__`, `eval`, or imports.
  - `generate_image`: Outbound GET requests to Pollinations Flux/Turbo.
  - `remember_user_fact`: Restricted to modifying `MEMORY.md`.
  - `manage_notes`: Restricted to reading/writing markdown files within `workspace/notes/user_<id>/`.
  - `set_reminder`: Schedules time-triggered jobs within OpenClaw automations.
  - `file_read` / `file_write`: Sandboxed strictly to `workspace/`.
- **Prohibited & Denied Tools (Deferred Capabilities):**
  - `shell`, `bash`, `exec`, `terminal`: **Strictly Disabled**.
  - `browser` / Chromium automation: **Strictly Disabled** (zero Chromium overhead).
  - Unrestricted external API calls: **Disabled**.
  - Autonomous financial or destructive transactions: **Disabled**.

### 2.2 Filesystem Sandboxing
- All file I/O operations are rooted at `/data/workspace`.
- Any relative path path-traversal attempt (e.g. `../../etc/passwd` or `../../proc/self/environ`) is rejected by the OpenClaw sandbox engine before disk access occurs.

### 2.3 Access Control & Channel Security
- **Telegram Whitelist:**
  - `dmPolicy: "whitelist"` enforces that only authorized user IDs (configured in `ALLOWED_USER_IDS` / `allowedUsers: ["5556841083"]`) can initiate commands.
  - Unrecognized users are rejected or presented with pairing requirements.
- **Group Privacy:**
  - In group chats, `requireMention: true` prevents the bot from eavesdropping or processing ambient group banter. Only explicit mentions (`@AiriSenseiBot`) or direct replies trigger execution.
- **Gateway Authentication:**
  - All external HTTP and WebSocket endpoints (`/v1/*`, `/tools/invoke`) require the `OPENCLAW_GATEWAY_TOKEN` Bearer token.
  - Public exposure without authentication is strictly blocked.

### 2.4 Secret Hygiene & Isolation
- Zero hardcoded secrets in the repository or Docker image layers.
- Secrets (`TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `OPENCLAW_GATEWAY_TOKEN`) are injected solely via environment variables.
- The agent prompt explicitly prohibits echoing API keys or internal configuration values.
