"""Unit tests for weather.py - parsing and range computation."""

import sys
import os

# Add pico directory to path so we can import weather module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pico"))

import json
import weather


TESTS_DIR = os.path.dirname(__file__)


def load_sample(filename):
    path = os.path.join(TESTS_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def test_build_url():
    url = weather.build_url(30.27, -97.74)
    assert "latitude=30.27" in url
    assert "longitude=-97.74" in url
    assert "minutely_15=temperature_2m,precipitation" in url
    assert "temperature_unit=fahrenheit" in url
    assert "past_minutely_15=4" in url
    assert "forecast_minutely_15=48" in url
    print("PASS: test_build_url")


def test_parse_dry_response():
    text = load_sample("sample_response.json")
    result = weather.parse_response(text)
    assert result is not None
    assert len(result["temperatures"]) == 52
    assert len(result["precipitations"]) == 52
    assert result["now_index"] == 4
    # Verify temperature values match sample
    assert result["temperatures"][0] == 79.5
    assert result["temperatures"][-1] == 70.0
    # Verify mostly dry
    assert sum(result["precipitations"]) < 1.0
    print("PASS: test_parse_dry_response")


def test_parse_rainy_response():
    text = load_sample("sample_rainy.json")
    result = weather.parse_response(text)
    assert result is not None
    assert len(result["temperatures"]) == 52
    # Verify rain exists
    assert max(result["precipitations"]) > 1.0
    # Peak rain should be 5.10
    assert abs(max(result["precipitations"]) - 5.10) < 0.01
    print("PASS: test_parse_rainy_response")


def test_parse_invalid_json():
    assert weather.parse_response("not json") is None
    assert weather.parse_response("") is None
    assert weather.parse_response(None) is None
    print("PASS: test_parse_invalid_json")


def test_parse_missing_fields():
    # Valid JSON but missing minutely_15
    assert weather.parse_response('{"latitude": 30.0}') is None
    # Has minutely_15 but missing temperature_2m
    assert weather.parse_response('{"minutely_15": {"precipitation": [0.0]}}') is None
    # Has temperature_2m but only 1 entry
    assert weather.parse_response(
        '{"minutely_15": {"time": ["t"], "temperature_2m": [70.0], "precipitation": [0.0]}}'
    ) is None
    print("PASS: test_parse_missing_fields")


def test_compute_ranges_dry():
    text = load_sample("sample_response.json")
    wd = weather.parse_response(text)
    ranges = weather.compute_ranges(wd)
    assert ranges is not None
    # Min should be ~69.7, max should be ~79.5
    assert 69.0 < ranges["min_temp"] < 70.0
    assert 79.0 < ranges["max_temp"] < 80.0
    # Current temp is at index 4 = 77.2
    assert abs(ranges["current_temp"] - 77.2) < 0.01
    # Temp range should be at least 20
    assert ranges["temp_range"] >= 20.0
    # Actual range is ~9.8, so padded range should be exactly 20
    assert abs(ranges["temp_range"] - 20.0) < 0.01
    # Max precip should be at least 12.7 (minimum ceiling)
    assert ranges["max_precip"] >= 12.7
    # n should be 52
    assert ranges["n"] == 52
    print("PASS: test_compute_ranges_dry")


def test_compute_ranges_rainy():
    text = load_sample("sample_rainy.json")
    wd = weather.parse_response(text)
    ranges = weather.compute_ranges(wd)
    assert ranges is not None
    # Temp range: 53.5 to 78.8 = 25.3 degrees, should NOT be padded
    assert ranges["temp_range"] > 20.0
    assert abs(ranges["temp_range"] - (ranges["max_temp"] - ranges["min_temp"])) < 0.01
    # Max precip is 5.10, below 12.7 ceiling
    assert ranges["max_precip"] >= 12.7
    print("PASS: test_compute_ranges_rainy")


def test_compute_ranges_none():
    assert weather.compute_ranges(None) is None
    print("PASS: test_compute_ranges_none")


def test_mismatched_array_lengths():
    """Verify arrays are truncated to shortest when lengths differ."""
    data = {
        "minutely_15": {
            "time": ["t1", "t2", "t3"],
            "temperature_2m": [70.0, 72.0, 74.0],
            "precipitation": [0.0, 0.5],  # shorter than temps
        }
    }
    result = weather.parse_response(json.dumps(data))
    assert result is not None
    assert len(result["temperatures"]) == 2
    assert len(result["precipitations"]) == 2
    print("PASS: test_mismatched_array_lengths")


def test_now_index_clamping():
    """Verify now_index is clamped if data has fewer entries than PAST_INTERVALS."""
    short_data = {
        "minutely_15": {
            "time": ["t1", "t2"],
            "temperature_2m": [70.0, 72.0],
            "precipitation": [0.0, 0.0],
        }
    }
    result = weather.parse_response(json.dumps(short_data))
    assert result is not None
    # Only 2 entries, now_index should be clamped to 1 (len-1)
    assert result["now_index"] == 1
    print("PASS: test_now_index_clamping")


if __name__ == "__main__":
    test_build_url()
    test_parse_dry_response()
    test_parse_rainy_response()
    test_parse_invalid_json()
    test_parse_missing_fields()
    test_compute_ranges_dry()
    test_compute_ranges_rainy()
    test_compute_ranges_none()
    test_mismatched_array_lengths()
    test_now_index_clamping()
    print("\nAll weather tests passed.")
