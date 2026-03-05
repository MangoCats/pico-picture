# wifi.py - WiFi connection management for Pico W
# Hardware-dependent: requires MicroPython network module

import network
import time

try:
    from rp2 import country as set_country
except ImportError:
    set_country = None


def connect(ssid, password, country_code="US", timeout=25, status_cb=None):
    """Connect to WiFi access point.

    Args:
        ssid: Network name
        password: Network password
        country_code: Regulatory country code (default "US")
        timeout: Max seconds to wait for connection
        status_cb: Optional callback(message_string) for status updates

    Returns:
        IP address string on success, None on failure.
    """
    if set_country is not None:
        set_country(country_code)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    wait = timeout
    while wait > 0:
        status = wlan.status()
        if status < 0 or status >= 3:
            break
        if status_cb:
            status_cb("WiFi connecting... " + str(wait))
        wait -= 1
        time.sleep(1)

    if wlan.status() != 3:
        if status_cb:
            status_cb("WiFi connection failed")
        return None

    ip = wlan.ifconfig()[0]
    if status_cb:
        status_cb(ssid + " " + ip)
    return ip


def is_connected():
    """Check if WiFi is currently connected."""
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()


def reconnect(ssid, password, country_code="US", timeout=25, status_cb=None):
    """Attempt to reconnect if disconnected. Returns IP or None."""
    if is_connected():
        wlan = network.WLAN(network.STA_IF)
        return wlan.ifconfig()[0]
    if status_cb:
        status_cb("Reconnecting WiFi...")
    return connect(ssid, password, country_code, timeout, status_cb)
