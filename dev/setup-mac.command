#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
# Live Caption — macOS Installer
# Double-click this file in Finder to run, or: ./setup-mac.command
# ────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  +-----------------------------------------------------+"
echo "  |   Live Caption — macOS Installer                     |"
echo "  |   Real-time Speech Captioning & Translation          |"
echo "  +-----------------------------------------------------+"
echo ""

# ──────────────────────────────────────────────
# Detect chip architecture
# ──────────────────────────────────────────────
ARCH=$(uname -m)
IS_APPLE_SILICON=0
if [ "$ARCH" = "arm64" ]; then
    IS_APPLE_SILICON=1
    CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Apple Silicon")
    echo "  Hardware: $CHIP (Apple Silicon)"
else
    CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Intel")
    echo "  Hardware: $CHIP (Intel)"
fi
echo ""

# ──────────────────────────────────────────────
# [1/6] Check Homebrew
# ──────────────────────────────────────────────
echo "  [1/6] Checking Homebrew..."
if command -v brew &>/dev/null; then
    echo "     OK: Homebrew found"
else
    echo "     Homebrew not found. Installing..."
    echo "     (You may be prompted for your password)"
    echo ""
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for this session (Apple Silicon default path)
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f "/usr/local/bin/brew" ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    echo "     OK: Homebrew installed"
fi

# ──────────────────────────────────────────────
# [2/6] Install system dependencies
# ──────────────────────────────────────────────
echo ""
echo "  [2/6] Installing system dependencies..."

# PortAudio (required for sounddevice/microphone access)
if brew list portaudio &>/dev/null 2>&1; then
    echo "     OK: PortAudio already installed"
else
    echo "     Installing PortAudio (for microphone access)..."
    brew install portaudio
    echo "     OK: PortAudio installed"
fi

# ──────────────────────────────────────────────
# [3/6] Check Python
# ──────────────────────────────────────────────
echo ""
echo "  [3/6] Checking Python..."
if command -v python3 &>/dev/null; then
    PY=python3
else
    echo "     Python 3 not found. Installing via Homebrew..."
    brew install python
    PY=python3
fi
PYVER=$($PY --version 2>&1)
echo "     OK: $PYVER"

# ──────────────────────────────────────────────
# [4/6] Create virtual environment + base deps
# ──────────────────────────────────────────────
echo ""
echo "  [4/6] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    $PY -m venv venv
    echo "     Created venv/"
fi
source venv/bin/activate
pip install --upgrade pip -q

echo "     Installing base packages..."
pip install fastapi "uvicorn[standard]" websockets sounddevice numpy requests python-multipart -q
echo "     OK: Base packages installed"

# ──────────────────────────────────────────────
# [5/6] Install speech recognition engine
# ──────────────────────────────────────────────
echo ""
echo "  [5/6] Installing speech recognition..."
echo ""

BACKEND="none"

if [ "$IS_APPLE_SILICON" -eq 1 ]; then
    echo "  +---------------------------------------------------------+"
    echo "  |  Apple Silicon detected!                                 |"
    echo "  |                                                          |"
    echo "  |  Your Mac can run Whisper with GPU acceleration          |"
    echo "  |  using Apple's Metal framework via MLX.                  |"
    echo "  |                                                          |"
    echo "  |  MLX Whisper (GPU):  ~95-97% accuracy, uses Metal GPU    |"
    echo "  |  Vosk (CPU):         ~85-90% accuracy, lighter weight    |"
    echo "  +---------------------------------------------------------+"
    echo ""
    read -rp "  Install MLX Whisper for best quality? (Y/N): " INSTALL_MLX

    if [[ "$INSTALL_MLX" =~ ^[Yy]$ ]]; then
        echo ""
        echo "     Installing MLX Whisper (this may take a minute)..."
        pip install mlx-whisper -q
        echo "     OK: MLX Whisper installed (Metal GPU)"
        echo ""
        echo "     Note: The Whisper model (~1.6 GB) will download"
        echo "     automatically the first time you run the server."
        BACKEND="mlx"
    else
        echo ""
        echo "     Installing Vosk instead..."
        pip install vosk -q
        echo "     OK: Vosk installed (CPU mode)"
        echo ""
        echo "     Note: The Vosk model (~1.8 GB) will download"
        echo "     automatically the first time you run the server."
        BACKEND="vosk"
    fi
else
    # Intel Mac — no Metal GPU acceleration for MLX
    echo "  +---------------------------------------------------------+"
    echo "  |  Intel Mac detected.                                     |"
    echo "  |                                                          |"
    echo "  |  MLX Whisper requires Apple Silicon (M1/M2/M3/M4).      |"
    echo "  |  Your best option is Vosk (CPU-optimized streaming).     |"
    echo "  |                                                          |"
    echo "  |  Vosk (CPU):  ~85-90% accuracy, real-time streaming      |"
    echo "  +---------------------------------------------------------+"
    echo ""
    read -rp "  Install Vosk CPU voice-to-text? (Y/N): " INSTALL_VOSK

    if [[ "$INSTALL_VOSK" =~ ^[Yy]$ ]]; then
        echo ""
        echo "     Installing Vosk..."
        pip install vosk -q
        echo "     OK: Vosk installed"
        BACKEND="vosk"
    else
        echo ""
        echo "     Skipped. Install manually later: pip install vosk"
        BACKEND="none"
    fi
fi

# ──────────────────────────────────────────────
# [6/6] First-run configuration
# ──────────────────────────────────────────────
echo ""
echo "  [6/6] Configuration"
echo ""

if [ -f config.json ]; then
    echo "     Existing config.json found — keeping current settings."
    echo "     Edit in Operator Panel at http://localhost:3001"
else
    echo "     First-time setup:"
    echo ""
    read -rp "     DeepL API Key (free at deepl.com/pro-api, Enter to skip): " DEEPL_KEY
    read -rp "     Session title (Enter for 'Live Captioning'): " SESSION
    SESSION="${SESSION:-Live Captioning}"

    cat > config.json << CFGEOF
{
  "deepl_api_key": "$DEEPL_KEY",
  "session_title": "$SESSION",
  "input_lang": "EN",
  "target_lang": "ES",
  "translation_count": 1,
  "translations": [{"lang": "ES", "color": "#FFD54F"}],
  "speakers": [],
  "footer_image": null,
  "font_size": 42,
  "max_lines": 3,
  "bg_color": "#00004D",
  "font_family": "atkinson",
  "caption_color": "#FFFFFF",
  "backend": "$BACKEND"
}
CFGEOF
    echo ""
    echo "     OK: Config saved."
fi

chmod +x run-mac.command 2>/dev/null || true

# ──────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────
echo ""
echo "  ====================================================="
echo "   Setup complete!"
echo ""
if [ "$BACKEND" = "mlx" ]; then
    echo "   Engine: MLX Whisper (Apple Metal GPU — best quality)"
elif [ "$BACKEND" = "vosk" ]; then
    echo "   Engine: Vosk (CPU streaming — good quality)"
else
    echo "   WARNING: No speech engine installed yet."
    echo "   Install one:"
    echo "     pip install mlx-whisper    (Apple Silicon GPU)"
    echo "     pip install vosk           (CPU)"
fi
echo ""
echo "   To start:    double-click run-mac.command"
echo "                or: ./run-mac.command"
echo ""
echo "   Display:     http://localhost:3000"
echo "   Operator:    http://localhost:3001"
echo "  ====================================================="
echo ""
read -rp "  Press Enter to close..."
