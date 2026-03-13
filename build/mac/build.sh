#!/bin/bash
# ════════════════════════════════════════════════════════
# LinguaTaxi — macOS DMG Builder
#
# Prerequisites:
#   - macOS 12+ with Xcode Command Line Tools
#   - Optional: create-dmg (brew install create-dmg) for fancy DMG
#
# Output: dist/LinguaTaxi-1.0.0.dmg
# ════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_DIR/dist/mac_build"
APP_BUNDLE="$BUILD_DIR/LinguaTaxi.app"
DIST_DIR="$PROJECT_DIR/dist"
VERSION="1.0.0"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║  LinguaTaxi — macOS DMG Builder              ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# ── Clean ──
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# ── Create .app bundle structure ──
echo "  Creating app bundle..."
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
mkdir -p "$APP_BUNDLE/Contents/Resources/uploads"
mkdir -p "$APP_BUNDLE/Contents/Resources/models"

# Copy Info.plist
cp "$SCRIPT_DIR/Info.plist" "$APP_BUNDLE/Contents/"

# Copy launcher script
cp "$SCRIPT_DIR/launcher.sh" "$APP_BUNDLE/Contents/MacOS/LinguaTaxi"
chmod +x "$APP_BUNDLE/Contents/MacOS/LinguaTaxi"

# Copy application files
cp "$PROJECT_DIR/server.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/launcher.pyw" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/display.html" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/operator.html" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/dictation.html" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/requirements.txt" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/download_models.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/tuned_models.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/offline_translate.py" "$APP_BUNDLE/Contents/Resources/"

# ── Icon ──
if [ -f "$PROJECT_DIR/assets/linguataxi.icns" ]; then
    cp "$PROJECT_DIR/assets/linguataxi.icns" "$APP_BUNDLE/Contents/Resources/"
    echo "  [OK] Icon copied"
elif [ -f "$PROJECT_DIR/assets/linguataxi.png" ]; then
    # Convert PNG to ICNS
    echo "  Converting PNG icon to ICNS..."
    ICONSET="$BUILD_DIR/linguataxi.iconset"
    mkdir -p "$ICONSET"
    sips -z 16 16     "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_16x16.png" 2>/dev/null
    sips -z 32 32     "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_16x16@2x.png" 2>/dev/null
    sips -z 32 32     "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_32x32.png" 2>/dev/null
    sips -z 64 64     "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_32x32@2x.png" 2>/dev/null
    sips -z 128 128   "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_128x128.png" 2>/dev/null
    sips -z 256 256   "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_128x128@2x.png" 2>/dev/null
    sips -z 256 256   "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_256x256.png" 2>/dev/null
    sips -z 512 512   "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_256x256@2x.png" 2>/dev/null
    sips -z 512 512   "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_512x512.png" 2>/dev/null
    sips -z 1024 1024 "$PROJECT_DIR/assets/linguataxi.png" --out "$ICONSET/icon_512x512@2x.png" 2>/dev/null
    iconutil -c icns "$ICONSET" -o "$APP_BUNDLE/Contents/Resources/linguataxi.icns"
    rm -rf "$ICONSET"
    echo "  [OK] Icon converted"
else
    echo "  NOTE: No icon found. Place linguataxi.png or .icns in assets/"
fi

# ── Create DMG ──
DMG_NAME="LinguaTaxi-${VERSION}.dmg"
DMG_PATH="$DIST_DIR/$DMG_NAME"

echo "  Creating DMG..."

if command -v create-dmg &>/dev/null; then
    # Fancy DMG with create-dmg
    create-dmg \
        --volname "LinguaTaxi" \
        --volicon "$APP_BUNDLE/Contents/Resources/linguataxi.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "LinguaTaxi.app" 175 180 \
        --app-drop-link 425 180 \
        --hide-extension "LinguaTaxi.app" \
        --background "$PROJECT_DIR/assets/dmg_background.png" \
        "$DMG_PATH" \
        "$BUILD_DIR/" \
        2>/dev/null || {
            # Fallback without background if image missing
            create-dmg \
                --volname "LinguaTaxi" \
                --window-pos 200 120 \
                --window-size 600 400 \
                --icon-size 100 \
                --icon "LinguaTaxi.app" 175 180 \
                --app-drop-link 425 180 \
                "$DMG_PATH" \
                "$BUILD_DIR/"
        }
else
    # Simple DMG with hdiutil
    echo "  (Install create-dmg for a prettier DMG: brew install create-dmg)"
    hdiutil create -volname "LinguaTaxi" \
        -srcfolder "$BUILD_DIR" \
        -ov -format UDZO \
        "$DMG_PATH"
fi

# ── Cleanup ──
rm -rf "$BUILD_DIR"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║  BUILD SUCCESSFUL!                            ║"
echo "  ║                                                ║"
echo "  ║  Output: dist/$DMG_NAME            ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
