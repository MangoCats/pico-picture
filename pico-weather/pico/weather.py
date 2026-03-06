# weather.py - Open-Meteo API client and response parser
# No hardware dependencies - runs on both MicroPython and CPython

try:
    import ujson as json
except ImportError:
    import json


# API configuration
API_BASE = "https://api.open-meteo.com/v1/forecast"
PAST_INTERVALS = 4      # 4 x 15min = 1 hour of past data
FORECAST_INTERVALS = 48  # 48 x 15min = 12 hours of forecast


def build_url(lat, lon):
    """Build the Open-Meteo API request URL."""
    return (
        API_BASE
        + "?latitude=" + str(lat)
        + "&longitude=" + str(lon)
        + "&minutely_15=temperature_2m,precipitation"
        + "&temperature_unit=fahrenheit"
        + "&past_minutely_15=" + str(PAST_INTERVALS)
        + "&forecast_minutely_15=" + str(FORECAST_INTERVALS)
    )


def parse_response(json_text):
    """Parse Open-Meteo JSON response into weather data dict.

    Returns dict with keys:
        temperatures: list of float (Fahrenheit)
        precipitations: list of float (mm)
        now_index: int (index of "now" in the arrays)
    Returns None on parse failure.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return None

    m15 = data.get("minutely_15")
    if m15 is None:
        return None

    temps = m15.get("temperature_2m")
    precips = m15.get("precipitation")
    times = m15.get("time")

    if temps is None or precips is None or times is None:
        return None
    if len(temps) < 2 or len(precips) < 1:
        return None
    # Truncate to shortest array to prevent index errors in renderer
    n = min(len(temps), len(precips), len(times))
    temps = temps[:n]
    precips = precips[:n]

    # now_index: the number of past intervals requested
    # (first PAST_INTERVALS entries are past data, rest are forecast)
    now_index = min(PAST_INTERVALS, len(temps) - 1)

    return {
        "temperatures": temps,
        "precipitations": precips,
        "now_index": now_index,
    }


def compute_ranges(weather_data):
    """Compute display ranges from weather data.

    Returns dict with keys:
        min_temp, max_temp: actual min/max in the data
        temp_range: display range (at least 20 degrees)
        temp_base: bottom of display range
        max_precip: display ceiling for precipitation (at least 12.7mm)
        current_temp: temperature at now_index
        now_index: pass-through
        n: number of data points
    Returns None if weather_data is None.
    """
    if weather_data is None:
        return None

    temps = weather_data["temperatures"]
    precips = weather_data["precipitations"]
    now_index = weather_data["now_index"]

    min_temp = min(temps)
    max_temp = max(temps)
    max_precip = max(precips) if precips else 0.0

    # Enforce minimum ranges (matching existing Qt behavior)
    # 3.175 = 12.7mm/hr ceiling scaled to 15-minute intervals
    if max_precip < 3.175:
        max_precip = 3.175
    temp_range = max_temp - min_temp
    if temp_range < 20.0:
        temp_range = 20.0
    mid_temp = (min_temp + max_temp) * 0.5
    temp_base = mid_temp - temp_range * 0.5

    return {
        "min_temp": min_temp,
        "max_temp": max_temp,
        "temp_range": temp_range,
        "temp_base": temp_base,
        "max_precip": max_precip,
        "current_temp": temps[now_index],
        "now_index": now_index,
        "n": len(temps),
        "temperatures": temps,
        "precipitations": precips,
    }


def fetch_weather(lat, lon):
    """Fetch weather data from Open-Meteo. Returns parsed dict or None.

    This function requires network access. On MicroPython it uses urequests,
    on CPython it uses urllib. For testing, use parse_response() directly
    with sample data.
    """
    url = build_url(lat, lon)

    try:
        try:
            # Try MicroPython urequests first
            import urequests
            response = urequests.get(url)
            text = response.text
            response.close()
        except ImportError:
            # Fall back to CPython urllib
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(url, context=ctx) as response:
                text = response.read().decode("utf-8")
    except Exception:
        return None

    return parse_response(text)
