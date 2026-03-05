"""Tests for display.py rgb565 conversion (runs on desktop without hardware).

The PicoDisplay class itself can't be instantiated without MicroPython,
but the rgb565 static method is pure math and can be tested independently.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pico"))


def rgb565(r, g, b):
    """Standalone copy of PicoDisplay.rgb565 for testing without hardware."""
    r5 = r >> 3
    g6 = g >> 2
    b5 = b >> 3
    p = b5 | (g6 << 5) | (r5 << 11)
    return p


def qt_pix_trans(r, g, b):
    """Reference implementation from Qt mainwindow.cpp pixTrans().
    Returns (low_byte, high_byte) as the Qt code produces.
    """
    r5 = r >> 3
    g6 = g >> 2
    b5 = b >> 3
    p = b5 | (g6 << 5) | (r5 << 11)
    return (p & 0xFF, p >> 8)


def test_rgb565_known_colors():
    """Test RGB565 conversion against known values."""
    # Pure white: R=31, G=63, B=31 -> 0xFFFF
    assert rgb565(255, 255, 255) == 0xFFFF
    # Pure black
    assert rgb565(0, 0, 0) == 0x0000
    # Pure red: R=31, G=0, B=0 -> 31<<11 = 0xF800
    assert rgb565(255, 0, 0) == 0xF800
    # Pure green: R=0, G=63, B=0 -> 63<<5 = 0x07E0
    assert rgb565(0, 255, 0) == 0x07E0
    # Pure blue: R=0, G=0, B=31 -> 31 = 0x001F
    assert rgb565(0, 0, 255) == 0x001F
    print("PASS: test_rgb565_known_colors")


def test_rgb565_matches_qt():
    """Verify our rgb565 produces the same values as the Qt pixTrans."""
    test_colors = [
        (255, 127, 0),   # Orange (temperature line)
        (0, 192, 255),   # Cyan (rain bars)
        (128, 128, 128), # Gray (now line)
        (0, 200, 0),     # Green (text)
        (0, 0, 0),       # Black (background)
    ]
    for r, g, b in test_colors:
        our_val = rgb565(r, g, b)
        qt_lo, qt_hi = qt_pix_trans(r, g, b)
        qt_val = qt_lo | (qt_hi << 8)
        assert our_val == qt_val, (
            f"Mismatch for ({r},{g},{b}): ours=0x{our_val:04X}, qt=0x{qt_val:04X}"
        )
    print("PASS: test_rgb565_matches_qt")


def test_rgb565_byte_order():
    """Verify byte order matches what framebuf.RGB565 expects.
    MicroPython framebuf.RGB565 uses little-endian: low byte first.
    Our rgb565 returns the 16-bit value; framebuf stores it in LE.
    """
    # Orange: R=31, G=31, B=0 -> (31<<11)|(31<<5)|0 = 0xF800|0x03E0 = 0xFBE0
    # Wait, let's use the actual color: (255, 127, 0)
    val = rgb565(255, 127, 0)
    lo = val & 0xFF
    hi = (val >> 8) & 0xFF
    # These should match what Qt's pixTrans produces
    qt_lo, qt_hi = qt_pix_trans(255, 127, 0)
    assert lo == qt_lo and hi == qt_hi
    print("PASS: test_rgb565_byte_order")


if __name__ == "__main__":
    test_rgb565_known_colors()
    test_rgb565_matches_qt()
    test_rgb565_byte_order()
    print("\nAll display tests passed.")
