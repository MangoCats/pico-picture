# pico-weather

Standalone 12-hour weather forecast display for Raspberry Pi Pico W with
Waveshare LCD 1.14 (240x135, ST7789). Fetches weather data from the free
[Open-Meteo](https://open-meteo.com/) API — no API key required.

## What it shows

- Current temperature (large green digits, centered)
- 12-hour temperature trend line (orange, anti-aliased)
- High/low temperatures (small green digits, right side)
- Precipitation forecast (cyan bars along bottom)
- "Now" marker (gray vertical line)

Updates every 5 minutes over WiFi.

## Hardware

- Raspberry Pi Pico W
- [Waveshare Pico LCD 1.14](https://www.waveshare.com/wiki/Pico-LCD-1.14#Overview) (240x135 RGB565)

## Install

### Prerequisites

1. Flash MicroPython firmware onto your Pico W:
   - Hold BOOTSEL while plugging in via USB
   - Drag `rp2-pico-w-latest.uf2` onto the RPI-RP2 drive that appears
2. Install mpremote on your PC: `pip install mpremote`

### Deploy to Pico W

1. Create your config file:
   ```bash
   cd pico-weather/pico
   cp config_example.json config.json
   ```
2. Edit `config.json` with your WiFi credentials and location:
   ```json
   {
       "ssid": "YourNetworkName",
       "password": "YourNetworkPassword",
       "lat": 30.14,
       "lon": -81.55,
       "country": "US"
   }
   ```
3. Connect Pico W via USB and copy all files:
   ```bash
   python -m mpremote cp main.py weather.py renderer.py fonts.py display.py wifi.py config.json :
   ```
4. Reset the Pico to start: `python -m mpremote reset`

### Useful mpremote commands

- `python -m mpremote ls :` — list files on Pico
- `python -m mpremote repl` — interactive REPL
- `python -m mpremote run main.py` — run without copying
- `python -m mpremote reset` — soft-reset

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — system design, module responsibilities, data flow,
  memory budget, and hardware abstraction layer details
- [REQUIREMENTS.md](REQUIREMENTS.md) — project requirements and constraints
- [ROADMAP.md](ROADMAP.md) — development phases, decisions made, and technical debt log

## Development Environment

### Project structure

```
pico-weather/
├── pico/                    # Files deployed to the Pico W
│   ├── main.py              # Entry point (WiFi, fetch/render loop)
│   ├── weather.py           # Open-Meteo API client + JSON parsing
│   ├── renderer.py          # Weather visualization (all drawing logic)
│   ├── fonts.py             # Anti-aliased 2-bit bitmap font data
│   ├── display.py           # LCD hardware driver (ST7789 over SPI)
│   ├── wifi.py              # WiFi connection management
│   ├── config_example.json  # Template for config.json
│   └── config.json          # User config (not in git)
├── tests/                   # Desktop-only test files
│   ├── hal_desktop.py       # Pillow-based display backend for testing
│   ├── test_weather.py      # Weather parsing unit tests
│   ├── test_renderer.py     # Rendering tests with PNG output
│   ├── test_display.py      # RGB565 conversion tests
│   ├── test_memory.py       # Memory budget estimation
│   ├── test_integration.py  # Live API fetch + render end-to-end
│   ├── sample_response.json # Captured API response (dry weather)
│   ├── sample_rainy.json    # Synthetic response with precipitation
│   ├── requirements.txt     # CPython test dependencies
│   └── output/              # Generated test PNGs (gitignored)
├── tools/
│   └── generate_font.py     # Generates fonts.py from Arial Bold TrueType
└── simulator.py             # Tkinter live preview (no hardware needed)
```

### Running tests

```bash
pip install -r tests/requirements.txt
python -m pytest tests/ -v
```

22 tests across 5 suites: weather parsing, rendering, display conversion,
memory budget, and live API integration.

Renderer tests produce PNG files in `tests/output/` for visual verification.

### Desktop simulator

Preview the display in a tkinter window without Pico hardware:

```bash
pip install Pillow
python simulator.py [lat] [lon]
```

### Regenerating fonts

The anti-aliased bitmap fonts in `fonts.py` are generated from Arial Bold.
To regenerate (e.g. after changing glyph sizes):

```bash
python tools/generate_font.py           # writes pico/fonts.py
python tools/generate_font.py --preview  # also saves glyph preview PNGs
```

### Architecture overview

All rendering code (`renderer.py`, `fonts.py`) is hardware-independent and
operates against an abstract display interface. Three backends implement this
interface:

- `display.py` — Pico hardware (SPI framebuffer, RGB565)
- `tests/hal_desktop.py` — Pillow (for tests, produces PNGs)
- `simulator.py` — Tkinter (live desktop preview)

Weather data flows through: `weather.py` (fetch + parse) → `renderer.py`
(draw) → display backend (show). The main loop in `main.py` runs this cycle
every 5 minutes with WiFi reconnection and error recovery.
