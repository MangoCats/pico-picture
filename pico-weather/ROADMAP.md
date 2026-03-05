# PicoWeather Standalone - Development Roadmap

**Last updated**: 2026-03-04

## Project Goal

Replace the two-component PicoWeather system (desktop app + Pico display
server) with a single MicroPython application running entirely on the
Raspberry Pi Pico W. Switch from Meteomatics to the free Open-Meteo API.

## Phase 1: Weather Data Client -- COMPLETE

**Objective**: Fetch and parse weather data from Open-Meteo, testable on
desktop without hardware.

### Deliverables
- [x] `pico/weather.py` -- URL builder, JSON parser, range computation,
      dual-runtime fetch (urequests on Pico, urllib on CPython)
- [x] `pico/config_example.json` -- configuration template
- [x] `tests/sample_response.json` -- captured real API response (dry weather)
- [x] `tests/sample_rainy.json` -- synthetic response with precipitation
- [x] `tests/test_weather.py` -- 9 unit tests covering parsing, ranges,
      edge cases, invalid input
- [x] `tests/test_integration.py` -- live API fetch + validation
- [x] `tests/requirements.txt` -- desktop test dependencies

### Test Results
- 10 unit tests: PASS
- 1 integration test (live API): PASS
- Live response: 52 data points, 15-min resolution, Austin TX

### Technical Notes
- Open-Meteo `minutely_15` endpoint confirmed working with
  `past_minutely_15` and `forecast_minutely_15` parameters
- Response is flat arrays (not nested like Meteomatics), simpler to parse
- `now_index` = `PAST_INTERVALS` (4), clamped for short responses

### Debt Resolved
- `fetch_weather` now catches network exceptions and returns `None`
- `parse_response` truncates arrays to shortest length to prevent
  index-out-of-bounds if API returns mismatched array lengths
- Added test for mismatched array length case

---

## Phase 2: Display Rendering -- COMPLETE

**Objective**: Port the weather visualization from Qt/C++ to Python,
testable on desktop via Pillow.

### Deliverables
- [x] `pico/renderer.py` -- weather visualization (temp line, rain bars,
      now marker, temperature text)
- [x] `pico/fonts.py` -- 5x7 bitmap digits with scalable rendering and
      `measure_string` for layout
- [x] `tests/hal_desktop.py` -- Pillow-based display backend for testing
- [x] `tests/test_renderer.py` -- 5 render tests with PNG output and
      programmatic color/region assertions
- [x] `tests/test_integration.py` -- updated with full live render pipeline

### Test Results
- 5 renderer tests: PASS (3 PNG outputs verified visually)
- 2 integration tests: PASS (live fetch + live render)
- All 10 weather unit tests: still PASS

### Key Decisions Made
- Smooth font: Anti-aliased 2-bit (4 alpha levels) bitmap glyphs generated
  from Arial Bold via Pillow (`tools/generate_font.py`). Large: 65x84px
  per glyph, Small: 22x28px. Base64-encoded in `fonts.py`, ~17KB decoded.
  Rendered pixel-by-pixel with 3 color intensity levels for smooth edges.
- `framebuf.line()` is adequate -- temperature trend renders correctly at
  native 240x135 without anti-aliasing (4x upscale was only needed for Qt's
  smooth downscale).
- Color abstraction: `color()` helper checks for `rgb565` method; renderer
  works with both RGB tuples (desktop) and RGB565 integers (Pico).

### Debt Resolved
- Temperature line Y-coordinates clamped to screen bounds
- String width measurement extracted to `fonts.measure_string()` to
  eliminate duplicated width calculations in renderer

---

## Phase 3: Integration and Main Loop -- COMPLETE

**Objective**: Wire everything together for standalone operation. Deploy
to Pico hardware.

### Deliverables
- [x] `pico/main.py` -- entry point, config loading, WiFi, main loop with
      error recovery, status display, gc.collect between cycles
- [x] `pico/wifi.py` -- connection, reconnection, status callbacks
- [x] `pico/display.py` -- LCD hardware driver adapted from pico-picture.py
      with ST7789 init, SPI framebuffer, backlight PWM, rgb565 conversion
- [x] `tests/test_display.py` -- 3 tests verifying rgb565 conversion matches
      Qt pixTrans byte-for-byte
- [x] `tests/test_integration.py` -- updated with full live render pipeline

### Test Results
- 3 display tests: PASS (rgb565 matches Qt pixTrans exactly)
- All 20 tests across 4 suites: PASS

### Key Decisions Made
- Timer: `time.sleep(300)` in main loop (simpler than machine.Timer,
  adequate for 5-minute cycle, no interrupt complexity)
- Status display: white 8x8 text on black background with 28-char line
  wrapping, shown during WiFi connect and error states
- Config: JSON file on flash (`config.json`), loaded at startup
- WiFi: single retry with 60s backoff on initial connect failure; periodic
  reconnect check in main loop

### Debt Resolved
- Added 10ms delays in ST7789 hardware reset sequence for reliability
- rgb565 encoding verified to match Qt pixTrans byte-for-byte (colors on
  the display match the existing Qt app's appearance)

### Known Issue (documented, not a bug)
- MicroPython framebuf.RGB565 stores LE uint16 on the RP2040, but ST7789
  expects BE over SPI. This causes a color channel rotation on-screen.
  Our rgb565() produces the same values as the Qt pixTrans, so colors will
  match the existing app's appearance. If exact color accuracy is needed
  later, a byte-swap in rgb565() would correct it.

---

## Phase 4: Robustness and Polish -- COMPLETE

**Objective**: Harden for unattended long-term operation.

### Deliverables
- [x] WiFi connection with configurable retry loop (5 attempts with 60s
      backoff on startup, periodic reconnect in main loop)
- [x] Graceful error display: stale-data indicator (red dot top-left),
      failure count in status messages
- [x] `gc.collect()` before and after each fetch/render cycle
- [x] Top-level exception handler displays fatal errors on LCD
- [x] Consecutive failure tracking for monitoring data freshness
- [x] `tests/test_memory.py` -- memory budget estimation verifying
      ~111KB peak usage fits within 210KB available (47% margin)
- [x] `tests/output/.gitignore` -- exclude generated PNGs from git
- [x] Final documentation review

### Test Results
- 1 memory test: PASS (47% RAM margin)
- All 22 tests across 5 suites: PASS

### Backlight Control
Deferred: `display.set_backlight(duty)` is implemented and available. Time-
based or button-driven dimming can be added later as the user sees fit
without architectural changes.

### Items Not Implemented (low value / user preference)
- Time-based backlight dimming: requires NTP or RTC, adds complexity
- Button input handling: hardware is wired but no use cases defined yet

---

## Process

Each phase follows this cycle:
1. Plan implementation
2. Build code + tests
3. Run all tests (unit + integration)
4. Visual verification of rendered output (Phases 2+)
5. Review for technical debt
6. Update ROADMAP.md, REQUIREMENTS.md, ARCHITECTURE.md
7. Proceed to next phase
