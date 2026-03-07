# LinguaTaxi — Live Caption & Translation

## What This Is
Real-time speech captioning system with up to 5 simultaneous DeepL translations.
Three-port web architecture: main display (:3000), operator panel (:3001), extended display (:3002).
Desktop GUI launcher (tkinter) manages the server subprocess and opens browser windows.

## Architecture

**server.py** (937 lines) — FastAPI/Uvicorn backend
- 3 speech backends: faster-whisper (NVIDIA CUDA), MLX Whisper (Apple Metal), Vosk (CPU fallback)
- Shared `_buffer_audio_loop()` for Whisper/MLX, separate streaming loop for Vosk
- Speaker change with 0.5s retroactive buffer splitting via `_check_speaker_change()`
- WebSocket broadcast to display/operator clients
- DeepL translation in parallel threads
- Transcript saving: one timestamped .txt per language via `_save_line()`
- Starts with both captioning and translation paused by default

**launcher.pyw** (799 lines) — tkinter desktop GUI
- Start/Stop server subprocess with log capture
- Browser launchers for operator/main/extended displays
- Settings: transcript directory, microphone, backend selection
- First-run model download dialog with progress UI
- Saves settings to platform-specific AppData/Library/config

**display.html** (209 lines) — audience-facing captions
- Scrolling text with inline speaker labels (name shown only on speaker change)
- Per-slot state tracking: lines[], lastSpeaker, interimEl
- WebSocket receives final/interim/translation messages with speaker field

**operator.html** (618 lines) — full control panel
- Session controls: GO LIVE (captioning) + Resume Translation (separate toggles)
- Speaker buttons with keyboard shortcuts (1-9, 0 to clear)
- Language configuration (up to 5 DeepL slots)
- Styling: 4 backgrounds, 5 fonts, 12 colors, 24-960px size, 1-8 lines
- Transcript save toggle
- Keyboard: L=live, P=translation pause, C=clear

**download_models.py** (164 lines) — first-run model downloader
- Detects installed backend (faster-whisper vs vosk)
- Downloads appropriate model (Whisper large-v3-turbo or Vosk small)
- Called by launcher.pyw on first "Start Server" if no model found

**Build system:**
- `build/windows/` — build.bat pre-builds Python+venv on build machine, installer.iss bundles everything via Inno Setup. Venv path fixup in [Code] section.
- `build/mac/` — build.sh creates .app bundle + DMG. launcher.sh handles first-run Homebrew Python install.

## Key Technical Details

- Audio: 16kHz mono float32 via sounddevice
- Speaker buffer splitting: split at `change_time - 0.5s`, transcribe old portion under old speaker, continue new portion under new speaker
- Vosk can't split buffers (stateful recognizer) — force-finalizes instead
- Translation runs in thread pool, one thread per language slot
- Config persisted in config.json (server-side) and launcher_settings.json (GUI-side)
- Transcript path: `~/Documents/LinguaTaxi Transcripts/` default, configurable via GUI or `--transcripts-dir` CLI arg or `LINGUATAXI_TRANSCRIPTS` env var

## Rules
1. Never remove existing code features without explicitly verifying first
2. Technical accuracy is paramount — never suggest ideas unless fundamentally sound and factually accurate
3. Code updates should show implementation reasoning and bug-finding
4. If a task requires more than 1 session for accuracy, say so upfront and explain the breakdown

# === COGNILAYER (auto-generated, do not delete) ===

## CogniLayer v4 Active
Persistent memory + code intelligence is ON.
ON FIRST USER MESSAGE in this session, briefly tell the user:
  'CogniLayer v4 active — persistent memory is on. Type /cognihelp for available commands.'
Say it ONCE, keep it short, then continue with their request.

## Tools — HOW TO WORK

FIRST RUN ON A PROJECT:
When DNA shows "[new session]" or "[first session]":
1. Run /onboard — indexes project docs (PRD, README), builds initial memory
2. Run code_index() — builds AST index for code intelligence
Both are one-time. After that, updates are incremental.
If file_search or code_search return empty → these haven't been run yet.

UNDERSTAND FIRST (before making changes):
- memory_search(query) → what do we know? Past bugs, decisions, gotchas
- code_context(symbol) → how does the code work? Callers, callees, dependencies
- file_search(query) → search project docs (PRD, README) without reading full files
- code_search(query) → find where a function/class is defined
Use BOTH memory + code tools for complete picture. They are fast — call in parallel.

BEFORE RISKY CHANGES (mandatory):
- Renaming, deleting, or moving a function/class → code_impact(symbol) FIRST
- Changing a function's signature or return value → code_impact(symbol) FIRST
- Modifying shared utilities used across multiple files → code_impact(symbol) FIRST
- ALSO: memory_search(symbol) → check for related decisions or known gotchas
Both required. Structure tells you what breaks, memory tells you WHY it was built that way.

AFTER COMPLETING WORK:
- memory_write(content) → save important discoveries immediately
  (error_fix, gotcha, pattern, api_contract, procedure, decision)
- session_bridge(action="save", content="Progress: ...; Open: ...")
DO NOT wait for /harvest — session may crash.

SUBAGENT MEMORY PROTOCOL:
When spawning Agent tool for research or exploration:
- Include in prompt: synthesize findings into consolidated memory_write(content, type, tags="subagent,<task-topic>") facts
  Assign a descriptive topic tag per subagent (e.g. tags="subagent,auth-review", tags="subagent,perf-analysis")
- Do NOT write each discovery separately — group related findings into cohesive facts
- Write to memory as the LAST step before return, not incrementally — saves turns and tokens
- Each fact must be self-contained with specific details (file paths, values, code snippets)
- When findings relate to specific files, include domain and source_file for better search and staleness detection
- End each fact with 'Search: keyword1, keyword2' — keywords INSIDE the fact survive context compaction
- Record significant negative findings too (e.g. 'no rate limiting exists in src/api/' — prevents repeat searches)
- Return: actionable summary (file paths, function names, specific values) + what was saved + keywords for memory_search
- If MCP tools unavailable or fail → include key findings directly in return text as fallback
- Launch subagents as foreground (default) for reliable MCP access — user can Ctrl+B to background later
Why: without this protocol, subagent returns dump all text into parent context (40K+ tokens).
With protocol, findings go to DB and parent gets ~500 token summary + on-demand memory_search.

BEFORE DEPLOY/PUSH:
- verify_identity(action_type="...") → mandatory safety gate
- If BLOCKED → STOP and ask the user
- If VERIFIED → READ the target server to the user and request confirmation

## VERIFY-BEFORE-ACT
When memory_search returns a fact marked ⚠ STALE:
1. Read the source file and verify the fact still holds
2. If changed → update via memory_write
3. NEVER act on STALE facts without verification

## Process Management (Windows)
- NEVER use `taskkill //F //IM node.exe` — kills ALL Node.js INCLUDING Claude Code CLI!
- Use: `npx kill-port PORT` or find PID via `netstat -ano | findstr :PORT` then `taskkill //F //PID XXXX`

## Git Rules
- Commit often, small atomic changes. Format: "[type] what and why"
- commit = Tier 1 (do it yourself). push = Tier 3 (verify_identity).

## Project DNA: LinguaTaxi
Stack: unknown
Style: [unknown]
Structure: assets, models, uploads
Deploy: [NOT SET]
Active: [new session]
Last: [first session]

# === END COGNILAYER ===
