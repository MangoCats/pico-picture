# main.py - PicoWeather Standalone entry point
# Runs on Raspberry Pi Pico W with Waveshare LCD 1.14

import machine
import time
import gc

try:
    import ujson as json
except ImportError:
    import json

import wifi
import weather
import renderer
from display import PicoDisplay

UPDATE_INTERVAL = 300  # 5 minutes in seconds
WIFI_RETRY_INTERVAL = 60  # seconds between WiFi retry attempts
MAX_WIFI_RETRIES = 5  # max retries before giving up on startup


def load_config():
    """Load configuration from config.json on flash filesystem."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def show_status(display, message):
    """Display a status message on screen (white text on black)."""
    black = display.rgb565(0, 0, 0)
    white = display.rgb565(255, 255, 255)
    display.fill(black)
    # Word-wrap long messages across multiple lines
    y = 20
    while message and y < 120:
        line = message[:28]
        message = message[28:]
        display.text(line, 10, y, white)
        y += 12
    display.show()


def connect_wifi(display, ssid, password, country_code):
    """Attempt WiFi connection with retries and status display.
    Returns IP address string on success, None after all retries exhausted.
    """
    def status_cb(msg):
        show_status(display, msg)

    for attempt in range(MAX_WIFI_RETRIES):
        ip = wifi.connect(ssid, password, country_code, status_cb=status_cb)
        if ip is not None:
            return ip
        remaining = MAX_WIFI_RETRIES - attempt - 1
        if remaining > 0:
            show_status(display, "WiFi failed. Retry " + str(attempt + 1)
                        + "/" + str(MAX_WIFI_RETRIES)
                        + " in " + str(WIFI_RETRY_INTERVAL) + "s...")
            time.sleep(WIFI_RETRY_INTERVAL)
    return None


def main():
    # LED on during startup
    led = machine.Pin("LED", machine.Pin.OUT)
    led.value(1)

    display = PicoDisplay()
    show_status(display, "PicoWeather starting...")

    # Load configuration
    config = load_config()
    if config is None:
        show_status(display, "ERROR: config.json missing or invalid")
        return

    ssid = config.get("ssid", "")
    password = config.get("password", "")
    lat = config.get("lat", 0.0)
    lon = config.get("lon", 0.0)
    country_code = config.get("country", "US")

    if not ssid:
        show_status(display, "ERROR: ssid not set in config.json")
        return

    # Connect to WiFi with retries
    ip = connect_wifi(display, ssid, password, country_code)
    if ip is None:
        show_status(display, "WiFi failed after " + str(MAX_WIFI_RETRIES)
                    + " attempts. Reset to retry.")
        return

    # LED off once connected
    led.value(0)

    show_status(display, "Connected: " + ip + " Fetching weather...")

    last_ranges = None
    consecutive_failures = 0

    # Main loop
    while True:
        gc.collect()

        # Ensure WiFi is still connected
        def status_cb(msg):
            show_status(display, msg)

        reconnected_ip = wifi.reconnect(ssid, password, country_code,
                                        status_cb=status_cb)
        if reconnected_ip is None:
            show_status(display, "WiFi lost. Retry in "
                        + str(WIFI_RETRY_INTERVAL) + "s...")
            time.sleep(WIFI_RETRY_INTERVAL)
            continue

        # Fetch weather data
        wd = weather.fetch_weather(lat, lon)
        if wd is not None:
            ranges = weather.compute_ranges(wd)
            if ranges is not None:
                last_ranges = ranges
                consecutive_failures = 0
            else:
                consecutive_failures += 1
        else:
            consecutive_failures += 1

        # Render (use last good data if current fetch failed)
        if last_ranges is not None:
            renderer.render_weather(display, last_ranges)
            if consecutive_failures > 0:
                # Show a small indicator that data is stale
                red = display.rgb565(255, 0, 0)
                display.fill_rect(0, 0, 3, 3, red)
                display.show()
        else:
            show_status(display, "Waiting for weather data..."
                        + " (attempt " + str(consecutive_failures) + ")")

        gc.collect()

        # Sleep until next update
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Last-resort error display
        try:
            display = PicoDisplay()
            show_status(display, "FATAL: " + str(e))
        except Exception:
            pass
