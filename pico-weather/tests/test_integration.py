"""Integration test - fetches live data from Open-Meteo and validates it."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pico"))
sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image

import weather
import renderer
from hal_desktop import DesktopDisplay


TESTS_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(TESTS_DIR, "output")


def test_live_fetch():
    """Fetch real weather data for Austin, TX and validate the result."""
    print("Fetching live weather data from Open-Meteo...")
    result = weather.fetch_weather(30.14, -81.55)

    assert result is not None, "fetch_weather returned None"
    assert len(result["temperatures"]) >= 10, (
        f"Expected at least 10 temperature entries, got {len(result['temperatures'])}"
    )
    assert len(result["precipitations"]) >= 10, (
        f"Expected at least 10 precipitation entries, got {len(result['precipitations'])}"
    )

    # Sanity check temperature range (Austin TX: -10F to 120F is very generous)
    for i, t in enumerate(result["temperatures"]):
        assert -10 < t < 120, f"Temperature [{i}] = {t}F is out of sane range"

    # Precipitation should be non-negative
    for i, p in enumerate(result["precipitations"]):
        assert p >= 0, f"Precipitation [{i}] = {p}mm is negative"

    # Compute ranges
    ranges = weather.compute_ranges(result)
    assert ranges is not None
    assert ranges["temp_range"] >= 20.0
    assert ranges["max_precip"] >= 3.175
    assert ranges["n"] == len(result["temperatures"])

    print(f"  Data points: {ranges['n']}")
    print(f"  Current temp: {ranges['current_temp']:.1f}F")
    print(f"  Range: {ranges['min_temp']:.1f}F - {ranges['max_temp']:.1f}F")
    print(f"  Max precip: {max(result['precipitations']):.2f}mm")
    print("PASS: test_live_fetch")


def test_live_render():
    """Full pipeline: live API fetch -> parse -> compute -> render -> PNG."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Fetching live weather data for rendering...")
    result = weather.fetch_weather(30.14, -81.55)
    assert result is not None, "fetch_weather returned None"

    ranges = weather.compute_ranges(result)
    assert ranges is not None

    display = DesktopDisplay()
    renderer.render_weather(display, ranges)
    out_path = os.path.join(OUTPUT_DIR, "live_render.png")
    display.save(out_path)
    scaled = display.img.resize((240 * 4, 135 * 4), Image.NEAREST)
    out_4x = os.path.join(OUTPUT_DIR, "live_render_4x.png")
    scaled.save(out_4x)
    print(f"  Rendered live weather to {out_path}")
    print(f"  Current: {ranges['current_temp']:.0f}F, "
          f"Range: {ranges['min_temp']:.0f}-{ranges['max_temp']:.0f}F")
    print("PASS: test_live_render")


if __name__ == "__main__":
    test_live_fetch()
    test_live_render()
    print("\nAll integration tests passed.")
