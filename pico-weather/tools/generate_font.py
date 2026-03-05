"""Generate anti-aliased bitmap font data for PicoWeather.

Renders digits 0-9 and minus sign from a TrueType font using Pillow,
quantizes to 2-bit (4 alpha levels), and outputs a Python module with
base64-encoded glyph data.

Usage:
    python tools/generate_font.py [--preview]

    --preview  Also save preview PNGs showing all glyphs at each size.
"""

import sys
import os
import base64
from PIL import Image, ImageFont, ImageDraw

# Font to use (Arial Bold for clean, readable digits)
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"

# Target glyph cell sizes (must match what renderer.py expects)
LARGE_HEIGHT = 84  # matches current visual size
SMALL_HEIGHT = 28

# Characters to generate
CHARS = "0123456789-"


def render_glyph(font, ch, cell_w, cell_h):
    """Render a single character centered in a cell, return grayscale Image."""
    img = Image.new("L", (cell_w, cell_h), 0)
    draw = ImageDraw.Draw(img)

    # Get the bounding box for this character
    bbox = font.getbbox(ch)
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]

    # Center in cell
    x = (cell_w - char_w) // 2 - bbox[0]
    y = (cell_h - char_h) // 2 - bbox[1]

    draw.text((x, y), ch, fill=255, font=font)
    return img


def find_font_size(target_height):
    """Find the TrueType point size that fills the target pixel height."""
    for pt in range(8, 200):
        font = ImageFont.truetype(FONT_PATH, pt)
        # Measure tallest digit
        max_h = 0
        for ch in "0123456789":
            bbox = font.getbbox(ch)
            h = bbox[3] - bbox[1]
            if h > max_h:
                max_h = h
        if max_h >= target_height - 2:  # allow 2px margin
            return pt, font
    return 200, ImageFont.truetype(FONT_PATH, 200)


def find_cell_width(font):
    """Find the maximum digit width to use as fixed cell width."""
    max_w = 0
    for ch in CHARS:
        bbox = font.getbbox(ch)
        w = bbox[2] - bbox[0]
        if w > max_w:
            max_w = w
    return max_w + 2  # 1px padding each side


def quantize_2bit(img):
    """Quantize grayscale image to 2-bit (4 levels) and pack into bytes.

    Levels: 0=transparent, 1=33%, 2=67%, 3=100%
    Packing: 4 pixels per byte, MSB first.
    """
    pixels = list(img.getdata())
    packed = []
    for i in range(0, len(pixels), 4):
        byte = 0
        for j in range(4):
            idx = i + j
            if idx < len(pixels):
                # Quantize 0-255 to 0-3
                level = (pixels[idx] * 3 + 127) // 255
            else:
                level = 0
            byte = (byte << 2) | level
        packed.append(byte)
    return bytes(packed)


def generate_font_set(target_height, label):
    """Generate all glyphs at a target height. Returns (width, height, dict of bytes)."""
    pt, font = find_font_size(target_height)
    cell_w = find_cell_width(font)
    cell_h = target_height

    print(f"  {label}: pt={pt}, cell={cell_w}x{cell_h}")

    glyphs = {}
    for ch in CHARS:
        img = render_glyph(font, ch, cell_w, cell_h)
        packed = quantize_2bit(img)
        glyphs[ch] = packed

    return cell_w, cell_h, glyphs, font


def generate_preview(cell_w, cell_h, glyphs, label, scale=4):
    """Save a preview PNG showing all glyphs."""
    n = len(CHARS)
    gap = 4
    total_w = n * cell_w + (n - 1) * gap
    preview = Image.new("RGB", (total_w * scale, cell_h * scale), (0, 0, 0))
    draw = ImageDraw.Draw(preview)

    for i, ch in enumerate(CHARS):
        data = glyphs[ch]
        x_off = i * (cell_w + gap)
        for row in range(cell_h):
            for col in range(cell_w):
                pix_idx = row * cell_w + col
                byte_idx = pix_idx >> 2
                shift = (3 - (pix_idx & 3)) << 1
                level = (data[byte_idx] >> shift) & 3
                if level > 0:
                    intensity = [0, 85, 170, 255][level]
                    color = (0, intensity, 0)  # green like the display
                    sx = (x_off + col) * scale
                    sy = row * scale
                    draw.rectangle([sx, sy, sx + scale - 1, sy + scale - 1],
                                   fill=color)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"font_preview_{label}.png")
    preview.save(path)
    print(f"  Preview saved: {path}")


def format_bytes_literal(data, line_width=76):
    """Format bytes as a base64 string literal."""
    encoded = base64.b64encode(data).decode("ascii")
    return encoded


def main():
    preview = "--preview" in sys.argv

    print("Generating smooth font data...")

    # Generate both sizes
    lg_w, lg_h, lg_glyphs, lg_font = generate_font_set(LARGE_HEIGHT, "large")
    sm_w, sm_h, sm_glyphs, sm_font = generate_font_set(SMALL_HEIGHT, "small")

    if preview:
        generate_preview(lg_w, lg_h, lg_glyphs, "large")
        generate_preview(sm_w, sm_h, sm_glyphs, "small")

    # Calculate data sizes
    lg_per = len(next(iter(lg_glyphs.values())))
    sm_per = len(next(iter(sm_glyphs.values())))
    total = (lg_per + sm_per) * len(CHARS)
    print(f"  Large: {lg_per} bytes/glyph, Small: {sm_per} bytes/glyph")
    print(f"  Total binary data: {total:,} bytes")

    # Generate Python source
    lines = []
    lines.append('"""Smooth anti-aliased bitmap font data for PicoWeather.')
    lines.append('')
    lines.append('Generated by tools/generate_font.py from Arial Bold.')
    lines.append('2-bit depth (4 alpha levels) for anti-aliased rendering.')
    lines.append('Digits 0-9 and minus sign only.')
    lines.append('"""')
    lines.append('')
    lines.append('try:')
    lines.append('    from ubinascii import a2b_base64')
    lines.append('except ImportError:')
    lines.append('    from base64 import b64decode as a2b_base64')
    lines.append('')
    lines.append(f'LARGE_WIDTH = {lg_w}')
    lines.append(f'LARGE_HEIGHT = {lg_h}')
    lines.append(f'SMALL_WIDTH = {sm_w}')
    lines.append(f'SMALL_HEIGHT = {sm_h}')
    lines.append('')

    # Encode glyph data
    for size_label, width, height, glyphs in [
        ("LARGE", lg_w, lg_h, lg_glyphs),
        ("SMALL", sm_w, sm_h, sm_glyphs),
    ]:
        lines.append(f'_{size_label}_DATA = {{')
        for ch in CHARS:
            b64 = format_bytes_literal(glyphs[ch])
            key = repr(ch)
            lines.append(f'    {key}: a2b_base64("{b64}"),')
        lines.append('}')
        lines.append('')

    # Add rendering functions
    lines.append('')
    lines.append('def draw_char(display, ch, x, y, colors, size="large"):')
    lines.append('    """Draw anti-aliased character.')
    lines.append('')
    lines.append('    Args:')
    lines.append('        display: display object with pixel() method')
    lines.append('        ch: character to draw')
    lines.append('        x, y: top-left position')
    lines.append('        colors: list of 3 colors [33%, 67%, 100%]')
    lines.append('        size: "large" or "small"')
    lines.append('    """')
    lines.append('    if size == "large":')
    lines.append('        w, h, data = LARGE_WIDTH, LARGE_HEIGHT, _LARGE_DATA.get(ch)')
    lines.append('    else:')
    lines.append('        w, h, data = SMALL_WIDTH, SMALL_HEIGHT, _SMALL_DATA.get(ch)')
    lines.append('    if data is None:')
    lines.append('        return')
    lines.append('    for row in range(h):')
    lines.append('        row_off = row * w')
    lines.append('        for col in range(w):')
    lines.append('            idx = row_off + col')
    lines.append('            level = (data[idx >> 2] >> ((3 - (idx & 3)) << 1)) & 3')
    lines.append('            if level:')
    lines.append('                display.pixel(x + col, y + row, colors[level - 1])')
    lines.append('')
    lines.append('')
    lines.append('def measure_string(text, size="large", spacing=2):')
    lines.append('    """Return pixel width of a string."""')
    lines.append('    if size == "large":')
    lines.append('        w = LARGE_WIDTH')
    lines.append('    else:')
    lines.append('        w = SMALL_WIDTH')
    lines.append('    n = len(text)')
    lines.append('    if n == 0:')
    lines.append('        return 0')
    lines.append('    return n * w + (n - 1) * spacing')
    lines.append('')
    lines.append('')
    lines.append('def draw_string(display, text, x, y, colors, size="large", spacing=2):')
    lines.append('    """Draw a string of characters."""')
    lines.append('    if size == "large":')
    lines.append('        w = LARGE_WIDTH')
    lines.append('    else:')
    lines.append('        w = SMALL_WIDTH')
    lines.append('    for ch in text:')
    lines.append('        draw_char(display, ch, x, y, colors, size)')
    lines.append('        x += w + spacing')
    lines.append('')

    # Write the output
    out_path = os.path.join(os.path.dirname(__file__), "..", "pico", "fonts.py")
    with open(out_path, "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    out_size = os.path.getsize(out_path)
    print(f"  Written: {out_path} ({out_size:,} bytes)")
    print("Done.")


if __name__ == "__main__":
    main()
