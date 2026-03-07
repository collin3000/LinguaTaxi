# 🚕 LinguaTaxi — Live Caption & Translation

Real-time speech captioning with up to 5 simultaneous translations, powered by Whisper (GPU) and DeepL.

## Features

- **Live captioning** with speaker identification and inline dialogue labels
- **Up to 5 simultaneous translations** via DeepL API (parallel threaded)
- **Three displays**: Main (caption + 2 translations), Extended (3+ overflow), Operator (full controls)
- **Cross-platform**: Windows (NVIDIA CUDA), macOS (Apple Metal), Linux (CPU fallback)
- **Styling**: 4 backgrounds, 5 fonts (CJK/Arabic), 12 colors, 24-960px, 1-8 visible lines
- **Scrolling captions** — text flows naturally, old lines scroll up
- **Transcript saving**: Separate timestamped file per language with speaker labels
- **Translation & captioning pause**: Configure everything before going live

## Installation

### Windows — Installer (Recommended)
1. Run `LinguaTaxi-Setup-1.0.exe` — handles all dependencies
2. Launch from Desktop or Start Menu → **LinguaTaxi**

### macOS — DMG
1. Open `LinguaTaxi-1.0.0.dmg`, drag to Applications
2. First launch installs dependencies (2-5 min). Grant mic permission when prompted.

### Manual Install (Linux / Advanced)
```bash
pip install fastapi uvicorn websockets sounddevice numpy requests python-multipart
pip install faster-whisper   # NVIDIA GPU
python launcher.pyw          # GUI launcher
```

## Usage

1. **Launch LinguaTaxi** → click **Start Server**
2. **Open Operator Controls** → configure languages, speakers, styling
3. **GO LIVE** → captioning starts (translation still paused)
4. **Resume Translation** → DeepL translations begin

**Keyboard shortcuts** (Operator panel): L=live toggle, P=translation pause, C=clear, 1-9=speakers

**Transcripts** save to `Documents/LinguaTaxi Transcripts/` (configurable in GUI).

## Building Installers

### Windows
Requires [Inno Setup 6+](https://jrsoftware.org/isinfo.php). Run `build\windows\build.bat` → outputs `dist\LinguaTaxi-Setup-1.0.exe`

### macOS
Run `build/mac/build.sh` → outputs `dist/LinguaTaxi-1.0.0.dmg` (optional: `brew install create-dmg` for styled DMG)

### Icons
Run `python assets/generate_icons.py` (needs Pillow). On macOS, convert PNG to ICNS with `iconutil`.

## Uninstalling

**Windows**: Start Menu → Uninstall. Checkboxes to keep transcripts and models.
**macOS**: Trash the app. Optionally delete `~/Library/Application Support/LinguaTaxi/` and `~/Documents/LinguaTaxi Transcripts/`.
