#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
# Live Caption — macOS Launcher
# Double-click this file in Finder to run, or: ./run-mac.command
# ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Add Homebrew to PATH if needed (Apple Silicon)
if [ -f "/opt/homebrew/bin/brew" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -f "/usr/local/bin/brew" ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

# macOS microphone note
echo ""
echo "  NOTE: macOS may ask for microphone permission."
echo "  If you see a popup, click 'Allow' for Terminal."
echo "  If audio doesn't work, check:"
echo "    System Settings > Privacy & Security > Microphone > Terminal"
echo ""

# Open operator panel in default browser after a short delay
(sleep 3 && open "http://localhost:3001") &

python3 server.py "$@"

# If server exits with error
if [ $? -ne 0 ]; then
    echo ""
    echo "  If you see errors, try:"
    echo "    ./run-mac.command --backend vosk       (CPU mode)"
    echo "    ./run-mac.command --list-mics           (check mic)"
    echo "    ./setup-mac.command                     (re-run setup)"
    echo ""
    read -rp "  Press Enter to close..."
fi
