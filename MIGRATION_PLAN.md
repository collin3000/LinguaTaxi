# LinguaTaxi → Claude Code Migration Plan

## Step 1: Set Up the Project Folder

Create the project folder and initialize it:

```
mkdir linguataxi
cd linguataxi
git init
```

Copy all files from the zip into this folder, preserving the structure.

## Step 2: Create CLAUDE.md

Create a `CLAUDE.md` file in the project root. This is the instructions file that Claude Code reads to understand the project. Paste in the project context — what it is, architecture, file roles, and rules.

Suggested content:

```markdown
# LinguaTaxi — Live Caption & Translation

## What This Is
Real-time speech captioning system with up to 5 simultaneous translations via DeepL.
Three-port web architecture: main display (:3000), operator panel (:3001), extended display (:3002).
Desktop GUI launcher (tkinter) manages the server process and opens browser windows.

## Architecture
- server.py (937 lines) — FastAPI/Uvicorn backend, 3 speech backends (faster-whisper GPU, MLX Apple Silicon, Vosk CPU), WebSocket broadcast, DeepL translation
- launcher.pyw (799 lines) — tkinter desktop GUI, starts/stops server, first-run model download
- display.html (209 lines) — audience-facing scrolling captions with inline speaker labels
- operator.html (618 lines) — full control panel (speakers, languages, styling, pause/live)
- download_models.py (164 lines) — detects backend, downloads appropriate speech model

## Key Behaviors
- Server starts with captioning AND translation both paused (operator configures, then goes live)
- Speaker changes use 0.5s retroactive buffer splitting for accurate attribution
- Transcripts save to ~/Documents/LinguaTaxi Transcripts/ (configurable)
- One transcript file per language per session

## Build System
- build/windows/ — Inno Setup installer (build.bat pre-builds Python+venv, installer.iss bundles everything)
- build/mac/ — DMG builder (build.sh creates .app bundle, launcher.sh handles first-run setup)

## Rules
1. Never remove existing features without explicit confirmation
2. Technical accuracy is paramount — don't suggest ideas unless fundamentally sound
3. Code changes should be discussed before implementation (show what changes and why)
4. If a task needs multiple sessions for accuracy, say so upfront
```

## Step 3: Open in VS Code with Claude Code

```
cd linguataxi
code .
```

Then open the Claude Code extension (Ctrl+Shift+P → "Claude Code: Open").

## Step 4: First Claude Code Session

Start by telling Claude Code to read the codebase:

> Read through the project files and confirm you understand the architecture. Start with CLAUDE.md, then server.py, launcher.pyw, display.html, and operator.html.

This gets it oriented before making any changes.

## Step 5: Continue Development

From here you work conversationally in Claude Code. Some immediate tasks to pick up:

- **Installer testing**: The build.bat pre-builds Python+venv on the build machine, Inno bundles it. The venv path fixup happens in the [Code] section of installer.iss. This needs real testing on a clean Windows machine.
- **macOS DMG**: build/mac/build.sh creates the .app bundle. First-run installs Python via Homebrew. Needs testing on macOS.
- **Model download UX**: launcher.pyw shows a progress dialog on first "Start Server" if no model found. Currently indeterminate progress bar — could show actual download percentage.

## File Inventory

| File | Lines | Role |
|------|-------|------|
| server.py | 937 | Backend engine — audio capture, transcription, translation, WebSocket |
| launcher.pyw | 799 | Desktop GUI — server management, browser launchers, settings |
| operator.html | 618 | Web control panel — speakers, languages, styling, pause/live |
| display.html | 209 | Audience caption display — scrolling text with speaker labels |
| download_models.py | 164 | First-run model downloader (Whisper or Vosk) |
| build/windows/installer.iss | ~160 | Inno Setup config |
| build/windows/build.bat | ~120 | Windows build script |
| build/mac/build.sh | ~130 | macOS DMG builder |
| build/mac/launcher.sh | ~120 | macOS .app entry point |
| build/mac/Info.plist | ~30 | macOS app metadata |
