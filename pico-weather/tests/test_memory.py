"""Memory estimation test - verifies peak RAM fits within Pico W constraints."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pico"))

TESTS_DIR = os.path.dirname(__file__)
PICO_RAM = 264 * 1024  # 264KB
MICROPYTHON_OVERHEAD = 60_000  # ~60KB for MicroPython runtime
AVAILABLE_RAM = PICO_RAM - MICROPYTHON_OVERHEAD


def test_memory_budget():
    """Estimate peak memory usage and verify it fits in Pico RAM."""

    # Framebuffer: 240 * 135 * 2 bytes
    framebuffer = 240 * 135 * 2
    assert framebuffer == 64_800

    # Load sample response to measure JSON size
    with open(os.path.join(TESTS_DIR, "sample_response.json"), "r") as f:
        json_text = f.read()
    json_size = len(json_text)

    # Parse to measure parsed data size
    data = json.loads(json_text)
    temps = data["minutely_15"]["temperature_2m"]
    precips = data["minutely_15"]["precipitation"]

    # On MicroPython, floats are 8 bytes, list overhead ~50 bytes per list
    # Plus ~28 bytes per float object
    float_size = 8 + 28  # object header + value on MicroPython
    list_overhead = 50 + len(temps) * 4  # pointer array
    temps_mem = list_overhead + len(temps) * float_size
    precips_mem = list_overhead + len(precips) * float_size

    # Font data: 2-bit anti-aliased bitmaps from Arial Bold
    # Large: 11 chars * 1365 bytes = 15,015; Small: 11 * 154 = 1,694
    fonts_mem = 17_000

    # Code modules (.mpy bytecode, estimated)
    code_mem = 15_000

    # HTTP response buffer (JSON + SSL overhead)
    http_buffer = json_size + 4_000  # SSL session adds ~4KB

    # Working memory (stack, temp variables, gc overhead)
    working_mem = 20_000

    # Compute ranges dict (references existing data, minimal overhead)
    ranges_mem = 500

    total = (framebuffer + temps_mem + precips_mem + fonts_mem +
             code_mem + http_buffer + working_mem + ranges_mem)

    print("Memory Budget Estimate:")
    print(f"  Framebuffer:     {framebuffer:>8,} bytes")
    print(f"  Temp array:      {temps_mem:>8,} bytes ({len(temps)} floats)")
    print(f"  Precip array:    {precips_mem:>8,} bytes ({len(precips)} floats)")
    print(f"  Font data:       {fonts_mem:>8,} bytes")
    print(f"  Code modules:    {code_mem:>8,} bytes")
    print(f"  HTTP buffer:     {http_buffer:>8,} bytes (JSON={json_size})")
    print(f"  Working memory:  {working_mem:>8,} bytes")
    print(f"  Ranges dict:     {ranges_mem:>8,} bytes")
    print(f"  ---")
    print(f"  Total estimated: {total:>8,} bytes")
    print(f"  Available RAM:   {AVAILABLE_RAM:>8,} bytes "
          f"({PICO_RAM//1024}KB - {MICROPYTHON_OVERHEAD//1024}KB overhead)")
    print(f"  Margin:          {AVAILABLE_RAM - total:>8,} bytes "
          f"({(AVAILABLE_RAM - total) * 100 // AVAILABLE_RAM}%)")

    assert total < AVAILABLE_RAM, (
        f"Estimated memory {total} exceeds available {AVAILABLE_RAM}"
    )
    # Ensure at least 30% margin for safety
    margin = (AVAILABLE_RAM - total) / AVAILABLE_RAM
    assert margin > 0.30, (
        f"Memory margin {margin:.0%} is below 30% safety threshold"
    )
    print("PASS: test_memory_budget")


if __name__ == "__main__":
    test_memory_budget()
    print("\nAll memory tests passed.")
