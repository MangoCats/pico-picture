"""Renderer tests - produces PNGs for visual inspection + programmatic checks."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pico"))
sys.path.insert(0, os.path.dirname(__file__))

import json
import weather
import renderer
import fonts
from hal_desktop import DesktopDisplay


TESTS_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(TESTS_DIR, "output")


def load_sample(filename):
    path = os.path.join(TESTS_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def pixels_in_region(display, x0, y0, x1, y1):
    """Return list of non-black pixels in a rectangular region."""
    nonblack = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if 0 <= x < display.WIDTH and 0 <= y < display.HEIGHT:
                px = display.img.getpixel((x, y))
                if px != (0, 0, 0):
                    nonblack.append((x, y, px))
    return nonblack


def has_color_in_region(display, x0, y0, x1, y1, target_r, target_g, target_b,
                        tolerance=50):
    """Check if any pixel in region is close to the target color."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            if 0 <= x < display.WIDTH and 0 <= y < display.HEIGHT:
                r, g, b = display.img.getpixel((x, y))
                if (abs(r - target_r) < tolerance and
                    abs(g - target_g) < tolerance and
                    abs(b - target_b) < tolerance):
                    return True
    return False


def test_render_dry():
    """Render dry weather data and verify key visual elements."""
    ensure_output_dir()
    text = load_sample("sample_response.json")
    wd = weather.parse_response(text)
    ranges = weather.compute_ranges(wd)
    display = DesktopDisplay()
    renderer.render_weather(display, ranges)
    out_path = os.path.join(OUTPUT_DIR, "render_dry.png")
    display.save(out_path)

    # Check: orange temperature line exists somewhere in the middle of screen
    assert has_color_in_region(display, 0, 0, 240, 135, 255, 127, 0), \
        "No orange temperature line found"

    # Check: gray now-line near x = (4 * 240) // 52 = ~18
    xn = (4 * 240) // 52
    assert has_color_in_region(display, xn - 2, 0, xn + 2, 135, 128, 128, 128), \
        "No gray now-line found at expected position"

    # Check: green text for current temp (centered in left portion of screen)
    assert has_color_in_region(display, 0, 0, 160, 120, 0, 200, 0), \
        "No green current temperature text found"

    # Check: green text in top-right (max temp)
    assert has_color_in_region(display, 180, 0, 240, 30, 0, 200, 0), \
        "No green max temp text in top-right"

    # Check: green text in bottom-right (min temp)
    assert has_color_in_region(display, 180, 110, 240, 135, 0, 200, 0), \
        "No green min temp text in bottom-right"

    print(f"PASS: test_render_dry (saved {out_path})")


def test_render_rainy():
    """Render rainy weather data and verify rain bars appear."""
    ensure_output_dir()
    text = load_sample("sample_rainy.json")
    wd = weather.parse_response(text)
    ranges = weather.compute_ranges(wd)
    display = DesktopDisplay()
    renderer.render_weather(display, ranges)
    out_path = os.path.join(OUTPUT_DIR, "render_rainy.png")
    display.save(out_path)

    # Check: cyan rain bars in the early portion of the screen (rain is in
    # intervals 3-12 out of 52, so roughly x=14 to x=55)
    assert has_color_in_region(display, 10, 80, 60, 135, 0, 192, 255), \
        "No cyan rain bars found in expected region"

    # Check: orange temperature line still exists
    assert has_color_in_region(display, 0, 0, 240, 135, 255, 127, 0), \
        "No orange temperature line found"

    print(f"PASS: test_render_rainy (saved {out_path})")


def test_render_none():
    """Render with None data should not crash."""
    display = DesktopDisplay()
    renderer.render_weather(display, None)
    # Screen should remain black
    nonblack = pixels_in_region(display, 0, 0, 240, 135)
    assert len(nonblack) == 0, "Screen should be black with None data"
    print("PASS: test_render_none")


def test_render_temp_line_spans_width():
    """Temperature line should span the full width of the display."""
    text = load_sample("sample_response.json")
    wd = weather.parse_response(text)
    ranges = weather.compute_ranges(wd)
    display = DesktopDisplay()
    renderer.render_weather(display, ranges)

    # Check left edge has orange
    assert has_color_in_region(display, 0, 0, 20, 135, 255, 127, 0), \
        "No orange pixels near left edge"
    # Check right edge has orange
    assert has_color_in_region(display, 220, 0, 240, 135, 255, 127, 0), \
        "No orange pixels near right edge"
    print("PASS: test_render_temp_line_spans_width")


def test_font_rendering():
    """Verify all digit characters render without error."""
    ensure_output_dir()
    display = DesktopDisplay()
    display.fill((0, 0, 0))
    x = 2
    for ch in "0123456789-":
        fonts.draw_char(display, ch, x, 2, 0, 200, 0, size="small")
        x += fonts.SMALL_WIDTH + 2
    out_path = os.path.join(OUTPUT_DIR, "font_test.png")
    display.save(out_path)

    # Verify some green pixels were drawn (check for full-intensity green)
    assert has_color_in_region(display, 0, 0, 240, 40, 0, 200, 0), \
        "No green font pixels found"
    print(f"PASS: test_font_rendering (saved {out_path})")


def test_render_triple_digits():
    """Render with 3-digit temperatures (103 current, 108 max) to verify layout."""
    ensure_output_dir()
    # Synthetic ranges dict with triple-digit temps
    n = 52
    temps = [100.0 + 4.0 * i / n for i in range(n)]  # 100 to ~104
    temps[n - 1] = 108.0  # max at end
    temps[20] = 95.0  # dip for visual interest
    ranges = {
        "n": n,
        "temperatures": temps,
        "precipitations": [0.0] * n,
        "now_index": 4,
        "temp_base": 85.0,
        "temp_range": 30.0,
        "max_precip": 3.175,
        "min_temp": 95.0,
        "max_temp": 108.0,
        "current_temp": 103.0,
    }
    display = DesktopDisplay()
    renderer.render_weather(display, ranges)
    out_path = os.path.join(OUTPUT_DIR, "render_triple_digits.png")
    display.save(out_path)

    # Check: green text exists for large current temp (103)
    assert has_color_in_region(display, 0, 0, 160, 135, 0, 200, 0), \
        "No green current temp text found"

    # Check: green small text in top-right (108)
    assert has_color_in_region(display, 160, 0, 240, 30, 0, 200, 0), \
        "No green max temp (108) in top-right"

    # Check: green small text in bottom-right (95)
    assert has_color_in_region(display, 180, 110, 240, 135, 0, 200, 0), \
        "No green min temp (95) in bottom-right"

    # Note: 3 large digits (199px) + 3 small digits (70px) = 269px > 240px,
    # so overlap is inevitable. Verify the centering math pins large_x to 0.
    large_w = fonts.measure_string("103", size="large")
    small_w = fonts.measure_string("108", size="small")
    small_col_x = 240 - small_w - 1
    large_x = (small_col_x - large_w) // 2
    assert large_x <= 0, \
        "Large text should be pinned to left edge for triple digits"

    from PIL import Image
    scaled = display.img.resize((240 * 4, 135 * 4), Image.NEAREST)
    scaled.save(os.path.join(OUTPUT_DIR, "render_triple_digits_4x.png"))
    print(f"PASS: test_render_triple_digits (saved {out_path})")


if __name__ == "__main__":
    test_render_dry()
    test_render_rainy()
    test_render_none()
    test_render_temp_line_spans_width()
    test_font_rendering()
    test_render_triple_digits()
    print("\nAll renderer tests passed.")
