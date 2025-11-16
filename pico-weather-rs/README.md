# PicoWeather Rust Edition

A Rust-based HTTP server replacement for the Qt C++ PicoWeather application. Fetches weather data from Meteomatics API and displays it on the Pico W display.

## Features

- HTTP server on port 5710
- Web-based configuration interface
- Fetches temperature and precipitation data from Meteomatics API
- Renders weather graphics:
  - Temperature trend line (orange)
  - Rain bars (cyan)
  - "Now" indicator line (gray)
- Automatic updates at configurable intervals
- Sends images directly to Pico W display via HTTP PUT

## Requirements

- Rust 1.70+
- Meteomatics API account (free tier available)
- Pico W running the pico-picture firmware

## Installation

```bash
cargo build --release
```

## Usage

```bash
cargo run --release
```

Then open your browser to `http://localhost:5710`

## Configuration

Via the web interface:

- **Lat/Lon**: Geographic coordinates for weather data
- **Screen Address**: IP address of your Pico W (e.g., `192.168.1.100`)
- **Username/Password**: Meteomatics API credentials
- **Interval**: Auto-update interval in minutes (5-60)
- **Privacy**: Hide credentials in the UI

## API Endpoints

- `GET /` - Web interface
- `GET /api/config` - Get configuration
- `POST /api/config` - Save configuration
- `POST /api/update` - Fetch weather data and update display
- `POST /api/send` - Send current image to display
- `GET /api/status` - Get current status
- `GET /api/preview` - Get preview image (base64 PNG)

## Differences from Qt C++ Version

- Web-based interface instead of Qt widgets
- Runs as HTTP server accessible from any device
- Configuration stored in memory (not persistent between restarts)
- Simplified font rendering (text labels not yet implemented)
- Same weather data source and rendering logic
- Faster build times
- No GUI framework dependencies

## Performance

The Rust version benefits from the optimized pixel loop in the pico-picture firmware, resulting in ~10 FPS refresh rates (vs. 0.3 FPS with the old implementation).

## License

See parent project LICENSE file.
