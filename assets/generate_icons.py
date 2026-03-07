#!/usr/bin/env python3
"""
Generate LinguaTaxi icon files (.ico for Windows, .png for macOS conversion).
Run: python generate_icons.py

Requires: pip install Pillow cairosvg  (for SVG rendering)
Fallback: generates a simple programmatic icon without SVG
"""

import struct, sys
from pathlib import Path

ASSETS_DIR = Path(__file__).parent

def generate_programmatic_icon(size):
    """Create a taxi-themed icon pixel by pixel. Returns RGBA bytes."""
    pixels = bytearray()
    cx, cy = size / 2, size / 2
    s = size / 512  # scale factor

    for y in range(size):
        for x in range(size):
            r, g, b, a = 26, 26, 46, 255  # Dark background

            # Rounded corners
            dx = max(0, abs(x - cx) - cx + 80 * s)
            dy = max(0, abs(y - cy) - cy + 80 * s)
            if (dx * dx + dy * dy) > (80 * s) ** 2:
                r, g, b, a = 0, 0, 0, 0
                pixels.extend([r, g, b, a])
                continue

            # Taxi body (yellow rectangle)
            if 200 * s < y < 320 * s and 100 * s < x < 412 * s:
                r, g, b = 255, 213, 79

                # Windows (dark cutouts)
                if 218 * s < y < 274 * s:
                    if 132 * s < x < 232 * s or 248 * s < x < 380 * s:
                        r, g, b = 22, 33, 62
                        # Caption lines in windows
                        wy = (y - 218 * s)
                        if 248 * s < x < 380 * s:
                            if 14 * s < wy < 18 * s and x < 368 * s:
                                r, g, b = 79, 195, 247
                            elif 24 * s < wy < 28 * s and x < 348 * s:
                                r, g, b = 129, 199, 132
                            elif 34 * s < wy < 38 * s and x < 356 * s:
                                r, g, b = 255, 138, 128
                        elif 132 * s < x < 232 * s:
                            if 14 * s < wy < 18 * s and x < 217 * s:
                                r, g, b = 79, 195, 247
                            elif 24 * s < wy < 28 * s and x < 205 * s:
                                r, g, b = 255, 213, 79

            # Taxi roof
            elif 168 * s < y < 208 * s and 180 * s < x < 332 * s:
                r, g, b = 255, 224, 130
                # Roof light
                ldx = (x - 256 * s)
                ldy = (y - 162 * s)
                if ldx * ldx + ldy * ldy < (14 * s) ** 2:
                    r, g, b = 79, 195, 247

            # Wheels
            for wx, wy in [(172, 320), (340, 320)]:
                wdx = x - wx * s
                wdy = y - wy * s
                dist = wdx * wdx + wdy * wdy
                if dist < (28 * s) ** 2:
                    if dist < (6 * s) ** 2:
                        r, g, b = 85, 85, 85
                    elif dist < (16 * s) ** 2:
                        r, g, b = 51, 51, 51
                    else:
                        r, g, b = 26, 26, 46

            # Speech bubble (top right)
            bx, by = x - 400 * s, y - 135 * s
            if bx * bx / (50 * s) ** 2 + by * by / (40 * s) ** 2 < 1 and y < 175 * s and x > 350 * s:
                r, g, b = 79, 195, 247
                # Text lines in bubble
                if 118 * s < y < 122 * s and 370 * s < x < 420 * s:
                    r, g, b = 255, 255, 255
                elif 128 * s < y < 132 * s and 370 * s < x < 408 * s:
                    r, g, b = 255, 255, 255

            pixels.extend([r, g, b, a])

    return bytes(pixels)


def create_ico(path, sizes=[16, 32, 48, 64, 128, 256]):
    """Create .ico file with multiple sizes."""
    try:
        from PIL import Image
        # Try SVG first
        svg_path = ASSETS_DIR / "linguataxi.svg"
        if svg_path.exists():
            try:
                import cairosvg
                png_data = cairosvg.svg2png(url=str(svg_path), output_width=256, output_height=256)
                import io
                base_img = Image.open(io.BytesIO(png_data))
                imgs = [base_img.resize((s, s), Image.LANCZOS) for s in sizes]
                imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
                print(f"  [OK] {path} (from SVG, {len(sizes)} sizes)")
                return True
            except ImportError:
                pass

        # Programmatic fallback with Pillow
        imgs = []
        for s in sizes:
            data = generate_programmatic_icon(s)
            img = Image.frombytes("RGBA", (s, s), data)
            imgs.append(img)
        imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
        print(f"  [OK] {path} (programmatic, {len(sizes)} sizes)")
        return True

    except ImportError:
        # Pure struct-based fallback (single size)
        print("  Pillow not available, creating basic 32x32 icon...")
        return _create_ico_raw(path)


def create_png(path, size=512):
    """Create PNG icon for macOS."""
    try:
        from PIL import Image
        svg_path = ASSETS_DIR / "linguataxi.svg"
        if svg_path.exists():
            try:
                import cairosvg
                cairosvg.svg2png(url=str(svg_path), write_to=str(path),
                                  output_width=size, output_height=size)
                print(f"  [OK] {path} (from SVG, {size}x{size})")
                return True
            except ImportError:
                pass

        data = generate_programmatic_icon(size)
        img = Image.frombytes("RGBA", (size, size), data)
        img.save(path, format="PNG")
        print(f"  [OK] {path} (programmatic, {size}x{size})")
        return True
    except ImportError:
        print(f"  SKIP: {path} — Pillow required for PNG generation")
        return False


def _create_ico_raw(path):
    """Create a minimal .ico without Pillow using raw BMP data."""
    w, h = 32, 32
    data = generate_programmatic_icon(w)

    # Convert RGBA to BGRA for BMP
    bgra = bytearray()
    for i in range(0, len(data), 4):
        bgra.extend([data[i + 2], data[i + 1], data[i], data[i + 3]])

    bmp_header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, len(bgra), 0, 0, 0, 0)

    # AND mask (1bpp transparency - all opaque since we use 32-bit alpha)
    and_mask = b'\x00' * (((w + 31) // 32) * 4 * h)

    image_data = bmp_header + bytes(bgra) + and_mask
    ico_header = struct.pack('<HHH', 0, 1, 1)
    ico_entry = struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(image_data), 22)

    with open(path, 'wb') as f:
        f.write(ico_header + ico_entry + image_data)

    print(f"  [OK] {path} (raw BMP, 32x32)")
    return True


if __name__ == "__main__":
    print("\n  LinguaTaxi — Icon Generator\n")

    ico_path = ASSETS_DIR / "linguataxi.ico"
    png_path = ASSETS_DIR / "linguataxi.png"

    create_ico(ico_path)
    create_png(png_path, 1024)

    print("\n  Done! Convert PNG to ICNS on macOS with:")
    print("    cd assets && mkdir icon.iconset")
    print("    sips -z 512 512 linguataxi.png --out icon.iconset/icon_512x512.png")
    print("    iconutil -c icns icon.iconset -o linguataxi.icns\n")
