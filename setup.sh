#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  +-----------------------------------------------------+"
echo "  |   Live Caption — Installer                           |"
echo "  |   Real-time Speech Captioning & Translation          |"
echo "  +-----------------------------------------------------+"
echo ""

# ──────────────────────────────────────────────
# Check Python
# ──────────────────────────────────────────────
echo "  [1/5] Checking Python..."
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "  ERROR: Python not found. Install Python 3.9+ first."
    echo "     macOS:  brew install python"
    echo "     Ubuntu: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
PYVER=$($PY --version 2>&1)
echo "     OK: $PYVER found"

# ──────────────────────────────────────────────
# Virtual environment + base deps
# ──────────────────────────────────────────────
echo ""
echo "  [2/5] Setting up virtual environment + base dependencies..."
if [ ! -d "venv" ]; then
    $PY -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install fastapi "uvicorn[standard]" websockets sounddevice numpy requests python-multipart -q
echo "     OK: Base packages installed"

# System audio dependency (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! dpkg -l libportaudio2 &>/dev/null 2>&1; then
        echo "     Installing PortAudio (required for audio capture)..."
        sudo apt-get install -y libportaudio2 portaudio19-dev 2>/dev/null || {
            echo "     WARNING: Could not install PortAudio automatically."
            echo "     Run: sudo apt install libportaudio2 portaudio19-dev"
        }
    fi
fi

# ──────────────────────────────────────────────
# Detect GPU capability
# ──────────────────────────────────────────────
echo ""
echo "  [3/5] Detecting GPU capability..."

GPU_CAPABLE=0
HAS_NVIDIA=0
HAS_CUDA=0
GPU_NAME="None"

if command -v nvidia-smi &>/dev/null; then
    HAS_NVIDIA=1
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo "     Found GPU: $GPU_NAME"

    # Check for CUDA libraries
    if ldconfig -p 2>/dev/null | grep -q libcublas; then
        HAS_CUDA=1
        echo "     Found CUDA libraries"
        GPU_CAPABLE=1
    else
        # Check if pip-installable CUDA libs could work
        echo "     WARNING: CUDA libraries not found in system path"
        echo ""
        echo "     Your GPU ($GPU_NAME) is present but CUDA libraries are missing."
        echo "     Options:"
        echo "       A) Install CUDA:  sudo apt install nvidia-cuda-toolkit"
        echo "          Or: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12"
        echo "          Then re-run this setup for Whisper (GPU, best quality)."
        echo "       B) Continue now with Vosk (CPU, good quality)."
        echo ""
    fi
else
    echo "     No NVIDIA GPU detected"
    echo ""
fi

# ──────────────────────────────────────────────
# Choose and install speech recognition backend
# ──────────────────────────────────────────────
echo "  [4/5] Installing speech recognition..."
echo ""

BACKEND="none"

if [ "$GPU_CAPABLE" -eq 1 ]; then
    echo "     Your system supports GPU-accelerated Whisper (best accuracy: ~95-97%)."
    echo "     Installing faster-whisper..."
    pip install "faster-whisper>=1.0.0" -q
    echo "     OK: Whisper installed (GPU mode)"
    BACKEND="whisper"
else
    echo "  +---------------------------------------------------------+"
    echo "  |  Your system does not have a sufficient GPU to use       |"
    echo "  |  Whisper voice-to-text.                                  |"
    echo "  |                                                          |"
    echo "  |  Would you like to install with a voice-to-text engine   |"
    echo "  |  that is compatible with your computer but will have     |"
    echo "  |  lower accuracy?                                         |"
    echo "  |                                                          |"
    echo "  |  Whisper (GPU):  ~95-97% accuracy, needs NVIDIA + CUDA   |"
    echo "  |  Vosk (CPU):     ~85-90% accuracy, works on any PC       |"
    echo "  |                  Real-time streaming, no GPU required     |"
    echo "  +---------------------------------------------------------+"
    echo ""
    read -rp "  Install Vosk CPU voice-to-text? (Y/N): " INSTALL_VOSK

    if [[ "$INSTALL_VOSK" =~ ^[Yy]$ ]]; then
        echo ""
        echo "     Installing Vosk..."
        pip install vosk -q
        echo "     OK: Vosk installed (CPU mode)"
        echo ""
        echo "     Note: The voice recognition model (~1.8 GB) will download"
        echo "     automatically the first time you run the server."
        BACKEND="vosk"
    else
        echo ""
        echo "     Skipping speech recognition install."
        echo "     Install manually later:"
        echo "       pip install vosk               (for CPU)"
        echo "       pip install faster-whisper     (for GPU, needs CUDA)"
        BACKEND="none"
    fi
fi

# ──────────────────────────────────────────────
# First-run config
# ──────────────────────────────────────────────
echo ""
echo "  [5/5] Configuration"
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

    cat > config.json <<CFGEOF
{
  "deepl_api_key": "$DEEPL_KEY",
  "session_title": "$SESSION",
  "target_lang": "ES",
  "speakers": [],
  "footer_image": null,
  "font_size": 42,
  "max_lines": 3,
  "backend": "$BACKEND"
}
CFGEOF
    echo ""
    echo "     OK: Config saved."
fi

chmod +x run.sh 2>/dev/null || true

echo ""
echo "  ====================================================="
echo "   Setup complete!"
echo ""
if [ "$BACKEND" = "whisper" ]; then
    echo "   Backend: Whisper (GPU-accelerated, best quality)"
elif [ "$BACKEND" = "vosk" ]; then
    echo "   Backend: Vosk (CPU, good quality)"
else
    echo "   WARNING: No speech engine installed yet."
    echo "   Install one: pip install vosk  OR  pip install faster-whisper"
fi
echo ""
echo "   To start:    ./run.sh"
echo "   Display:     http://localhost:3000"
echo "   Operator:    http://localhost:3001"
echo "  ====================================================="
echo ""
