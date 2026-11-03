# TOOLS.md: Workspace Tool Usage & Security Rules

## Available Capabilities & Routing

### 1. Web Search (`web_search`)
- Use whenever factual verification or fresh internet data is required.
- Construct queries using high-signal nouns and dates (e.g. `giá vàng SJC 2026`).
- Do not make repeated identical queries if the first fails; rephrase with alternative terms.

### 2. Deep Webpage Extraction (`read_webpage`)
- Must be used following `web_search` when exact figures, tables, or complete articles are required.
- Always cite the extracted URL in the final user response.

### 3. Safe Math Calculation (`calculate`)
- Compute all mathematical, tax, or financial equations using this tool.
- Supports basic arithmetic, `sqrt`, `sin`, `cos`, `tan`, `log`, `log10`, `exp`, `pi`, `e`, `abs`, `round`.
- Never guess large numbers or percentages.

### 4. AI Art Generation (`generate_image`)
- Translates and enhances Vietnamese image briefs into English descriptive prompts.
- Employs Pollinations Flux (1024x1024) with automatic fallback to Turbo if busy.

### 5. Persistent Memory (`remember_user_fact`)
- Stores user facts into `MEMORY.md`.
- Keys should be normalized (e.g., `ten_goi`, `cach_xung_ho`, `so_thich`).

### 6. Notes Management (`manage_notes`)
- Stores markdown files in `workspace/notes/user_<id>/`.
- Actions: `save`, `list`, `delete`, `search`.

### 7. Reminders (`set_reminder`)
- Schedules native one-shot notifications through OpenClaw automations.

---

## Security Boundaries & Prohibitions
- **Filesystem Access:** Strictly confined to `/data/workspace`.
- **Prohibited Operations:** Execution of arbitrary shell scripts, spawning background terminal processes, or performing destructive filesystem mutations outside the workspace.
- **Sensitive Secrets:** Never expose API keys, bot tokens, or gateway authentication tokens in tool outputs or chat messages.
