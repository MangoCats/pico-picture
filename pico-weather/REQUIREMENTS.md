# PicoWeather Standalone - Requirements Specification

**Version**: 0.1 (Pre-development)
**Date**: 2026-03-04
**Status**: Draft

## 1. Overview

PicoWeather Standalone is a self-contained weather display application running
entirely on a Raspberry Pi Pico W with a Waveshare Pico LCD 1.14 display. It
replaces the previous two-component architecture (desktop app + Pico display
server) with a single application that fetches weather data, renders a
graphical forecast, and drives the LCD directly.

## 2. Hardware Requirements

### 2.1 Target Platform
- Raspberry Pi Pico W (RP2040, 264KB SRAM, 2MB flash, WiFi)
- Waveshare Pico LCD 1.14 (ST7789 controller, 240x135 pixels, RGB565, SPI)

### 2.2 Hardware Interface
- SPI bus 1 at 10 MHz for LCD communication
- GPIO pins: CS=9, DC=8, RST=12, SCK=10, MOSI=11, BL=13 (PWM backlight)
- Optional: onboard LED for status indication
- Optional: hardware buttons (pins 2, 3, 15, 16, 17, 18, 20) for user input

## 3. Functional Requirements

### 3.1 Weather Data Acquisition

- **FR-01**: The application SHALL fetch weather forecast data over WiFi using
  HTTPS from a free, keyless weather API (Open-Meteo).
- **FR-02**: The application SHALL request temperature and precipitation data
  for a configurable geographic location (latitude/longitude).
- **FR-03**: The application SHALL retrieve forecast data covering at least 12
  hours into the future at no coarser than 1-hour resolution. Sub-hourly
  resolution (15 minutes) is preferred when available.
- **FR-04**: The application SHALL retrieve recent past data (at least 1 hour)
  to provide context on the temperature trend leading to "now."
- **FR-05**: Temperature data SHALL be in Fahrenheit.
- **FR-06**: Precipitation data SHALL be in millimeters.

### 3.2 Display Rendering

The display SHALL replicate the existing PicoWeather visualization:

- **FR-10**: The background SHALL be black.
- **FR-11**: A temperature trend line SHALL be drawn in orange (RGB 255,127,0)
  spanning the full width of the display, mapping time (past through future)
  on the X axis and temperature on the Y axis.
- **FR-12**: Precipitation SHALL be rendered as vertical bars in cyan
  (RGB 0,192,255) rising from the bottom of the display, with height
  proportional to precipitation amount scaled to the maximum value in the
  forecast window.
- **FR-13**: A vertical "now" marker line SHALL be drawn in gray
  (RGB 128,128,128) at the X position corresponding to the current time.
- **FR-14**: The current temperature SHALL be displayed as a large numeric
  value in green (RGB 0,200,0) at the top-left of the screen.
- **FR-15**: The forecast minimum and maximum temperatures SHALL be displayed
  as smaller numeric values in green at the right side of the screen (max at
  top-right, min at bottom-right).
- **FR-16**: Temperature range SHALL be padded to at least 20 degrees F to
  avoid excessive visual amplification of small variations.
- **FR-17**: Precipitation scale SHALL have a minimum ceiling of 12.7mm
  (0.5 inches) to avoid exaggerating light rain.

### 3.3 Update Cycle

- **FR-20**: The application SHALL refresh weather data and redisplay every 5
  minutes.
- **FR-21**: The display SHALL retain the last successfully rendered image if
  a data fetch fails.

### 3.4 Configuration

- **FR-30**: WiFi SSID and password SHALL be configurable.
- **FR-31**: Geographic location (latitude, longitude) SHALL be configurable.
- **FR-32**: Configuration SHALL be stored in a file on the Pico's flash
  filesystem (e.g., `config.json`).
- **FR-33**: The application SHALL function with the stored configuration
  without requiring any external computer after initial setup.

### 3.5 Startup and Status

- **FR-40**: On startup, the application SHALL display connection status on
  the LCD (WiFi connecting, IP address obtained, fetching data).
- **FR-41**: The onboard LED SHALL illuminate during startup and turn off once
  WiFi is connected (matching existing behavior).
- **FR-42**: On WiFi connection failure, the application SHALL retry
  periodically rather than halting.

## 4. Non-Functional Requirements

### 4.1 Memory

- **NF-01**: Peak RAM usage SHALL remain under 200KB to stay within the Pico
  W's 264KB SRAM with margin for MicroPython overhead.
- **NF-02**: The framebuffer (64,800 bytes) is the largest single allocation.
  Weather data structures and HTTP response buffers must fit alongside it.

### 4.2 Reliability

- **NF-10**: The application SHALL recover from transient WiFi disconnections
  without requiring a hardware reset.
- **NF-11**: The application SHALL handle malformed API responses gracefully
  (display last good data, log error).
- **NF-12**: The application SHALL use `gc.collect()` between update cycles to
  prevent memory fragmentation from accumulating.

### 4.3 Testability

- **NF-20**: Weather data parsing logic SHALL be pure Python with no hardware
  dependencies, testable under CPython on a development machine.
- **NF-21**: Rendering logic SHALL operate against an abstract display
  interface, allowing substitution of a Pillow-based backend for desktop
  testing and visual verification.
- **NF-22**: A captured sample API response SHALL be maintained for offline
  unit testing of the parsing pipeline.
- **NF-23**: Integration tests SHALL be executable on a development machine
  (CPython + Pillow), producing PNG output for visual inspection.

### 4.4 Security

- **NF-30**: WiFi credentials are stored in plaintext on the Pico's flash.
  This is acceptable given the device's physical-access threat model but
  should be documented.
- **NF-31**: No API keys or authentication tokens are required (Open-Meteo is
  keyless).

## 5. Weather API Specification

### 5.1 Provider: Open-Meteo

- Base URL: `https://api.open-meteo.com/v1/forecast`
- No API key required
- Free tier: 10,000 requests/day (application uses ~288/day at 5-min intervals)

### 5.2 Request Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `latitude` | User-configured | Location latitude |
| `longitude` | User-configured | Location longitude |
| `minutely_15` | `temperature_2m,precipitation` | 15-min resolution data |
| `temperature_unit` | `fahrenheit` | Temperature in F |
| `past_minutely_15` | `4` | Past 1 hour (4 x 15min) |
| `forecast_minutely_15` | `48` | Next 12 hours (48 x 15min) |

### 5.3 Response Format (relevant fields)

```json
{
  "minutely_15": {
    "time": ["2026-03-04T12:00", "2026-03-04T12:15", ...],
    "temperature_2m": [72.1, 72.3, ...],
    "precipitation": [0.0, 0.0, 0.2, ...]
  }
}
```

### 5.4 Fallback

If `minutely_15` is unavailable or unreliable, the application can fall back
to the `hourly` endpoint with parameters `temperature_2m,precipitation` and
`past_hours=1&forecast_hours=12`. This provides coarser (1-hour) resolution
but is guaranteed available.

## 6. Out of Scope

- No web-based configuration UI (configuration via file editing over USB)
- No persistent data logging or history
- No multi-location support
- No alerts or notifications
- No animation or frame rates beyond the 5-minute refresh
- No support for displays other than Waveshare Pico LCD 1.14

## 7. Development Status

| Requirement | Status |
|-------------|--------|
| FR-01 to FR-06 (Data Acquisition) | COMPLETE: parsing + live fetch verified |
| FR-10 to FR-17 (Display Rendering) | COMPLETE: all elements rendered, visually verified |
| FR-20 to FR-21 (Update Cycle) | COMPLETE: 5-min sleep loop with gc.collect |
| FR-30 to FR-33 (Configuration) | COMPLETE: config.json on flash |
| FR-40 to FR-42 (Startup/Status) | COMPLETE: status display + LED + WiFi retry with backoff |
| NF-01 to NF-02 (Memory) | COMPLETE: ~111KB estimated, 47% margin verified |
| NF-10 to NF-12 (Reliability) | COMPLETE: WiFi reconnect, stale-data indicator, gc.collect |
| NF-20 to NF-23 (Testability) | COMPLETE: 22 tests across 5 suites, all passing |
