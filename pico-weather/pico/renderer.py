# renderer.py - Weather visualization rendering
# No hardware dependencies - works with any display implementing the HAL interface

import fonts

SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135

# Colors as (R, G, B) tuples - converted to display format by color() helper
COLOR_BLACK = (0, 0, 0)
COLOR_ORANGE = (255, 127, 0)
COLOR_CYAN = (0, 192, 255)
COLOR_GRAY = (128, 128, 128)
COLOR_GREEN = (0, 200, 0)


def color(display, r, g, b):
    """Convert RGB to display-native color format."""
    if hasattr(display, "rgb565"):
        return display.rgb565(r, g, b)
    return (r, g, b)



def draw_aa_polyline(display, points, r, g, b, hw=0.75):
    """Draw anti-aliased connected line segments.

    Draws each segment directly with blend_pixel to avoid allocating a
    large dictionary (which can exceed MicroPython's memory).

    Args:
        display: display object with blend_pixel(x, y, r, g, b, a) method
        points: list of (x, y) integer coordinate tuples
        r, g, b: line color (0-255 each)
        hw: half-width in pixels (0.75 gives 1.5px effective width)
    """
    if len(points) < 2:
        return
    sw = SCREEN_WIDTH
    sh = SCREEN_HEIGHT
    threshold = hw + 0.5

    for seg in range(len(points) - 1):
        x0, y0 = points[seg]
        x1, y1 = points[seg + 1]
        dx = x1 - x0
        dy = y1 - y0
        steep = abs(dy) > abs(dx)

        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
            dx = x1 - x0
            dy = y1 - y0

        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
            dx = -dx
            dy = -dy

        if dx == 0:
            px, py = (y0, x0) if steep else (x0, y0)
            if 0 <= px < sw and 0 <= py < sh:
                display.blend_pixel(px, py, r, g, b, 255)
            continue

        grad = dy / dx

        for x in range(x0, x1 + 1):
            yc = y0 + (x - x0) * grad
            y_lo = int(yc - threshold)
            y_hi = int(yc + threshold) + 1

            for y in range(y_lo, y_hi):
                dist = abs(y - yc)
                if dist >= threshold:
                    continue
                if dist <= hw - 0.5:
                    a = 255
                else:
                    a = int((threshold - dist) * 255)
                if a <= 0:
                    continue
                if steep:
                    px, py = y, x
                else:
                    px, py = x, y
                if 0 <= px < sw and 0 <= py < sh:
                    display.blend_pixel(px, py, r, g, b, a)


def render_weather(display, ranges):
    """Render the weather visualization onto the display.

    Args:
        display: object implementing the HAL interface (fill, line, vline,
                 fill_rect, text, show, blend_pixel, and optionally rgb565)
        ranges: dict from weather.compute_ranges()
    """
    if ranges is None:
        return

    w = SCREEN_WIDTH
    h = SCREEN_HEIGHT
    n = ranges["n"]
    temps = ranges["temperatures"]
    precips = ranges["precipitations"]
    now_index = ranges["now_index"]
    temp_base = ranges["temp_base"]
    temp_range = ranges["temp_range"]
    max_precip = ranges["max_precip"]
    min_temp = ranges["min_temp"]
    max_temp = ranges["max_temp"]
    current_temp = ranges["current_temp"]

    c_black = color(display, *COLOR_BLACK)
    c_cyan = color(display, *COLOR_CYAN)
    c_gray = color(display, *COLOR_GRAY)

    # Clear screen
    display.fill(c_black)

    rain_margin = 0

    # Draw now line (gray vertical line)
    xn = (now_index * w) // n
    display.vline(xn, 0, h, c_gray)

    # 1) Precipitation bars (cyan, from bottom)
    for i in range(n):
        precip = precips[i] if i < len(precips) else 0.0
        if precip > 0.0:
            y_rain = int(((h - rain_margin) * precip) / max_precip)
            x0 = (i * w) // n
            x1 = ((i + 1) * w) // n
            bar_w = x1 - x0
            if bar_w < 1:
                bar_w = 1
            display.fill_rect(x0, h - rain_margin - y_rain,
                              bar_w, y_rain, c_cyan)

    # 2) Temperature text (drawn before line so line renders on top)
    max_str = str(int(round(max_temp)))
    min_str = str(int(round(min_temp)))
    max_w = fonts.measure_string(max_str, size="small")
    min_w = fonts.measure_string(min_str, size="small")

    # Small text column: right-aligned, use widest of max/min for alignment
    small_col_w = max(max_w, min_w)
    small_col_x = w - small_col_w - 1

    # Small max temperature (top-right, additive blend)
    fonts.draw_string(display, max_str, w - max_w - 1, 2,
                      *COLOR_GREEN, size="small")

    # Small min temperature (bottom-right, additive blend)
    min_h = fonts.SMALL_HEIGHT
    fonts.draw_string(display, min_str, w - min_w - 1, h - min_h - 1,
                      *COLOR_GREEN, size="small")

    # Large current temperature - centered vertically and horizontally
    # between left edge and the small text column (additive blend)
    current_str = str(int(round(current_temp)))
    large_text_w = fonts.measure_string(current_str, size="large")
    large_text_h = fonts.LARGE_HEIGHT
    large_x = (small_col_x - large_text_w) // 2
    if large_x < 0:
        large_x = 0
    large_y = (h - large_text_h) // 2
    fonts.draw_string(display, current_str, large_x, large_y,
                      *COLOR_GREEN, size="large")

    # 3) Temperature trend line (orange, 1.5px anti-aliased, drawn last)
    # Scale: rounded-up max at top, rounded-down min at bottom, min 20° range
    line_top = int(max_temp) + 1 if max_temp != int(max_temp) else int(max_temp)
    line_bot = int(min_temp) if min_temp >= 0 else int(min_temp) - 1
    line_range = line_top - line_bot
    if line_range < 20:
        pad = (20 - line_range) / 2.0
        line_top = line_top + pad
        line_bot = line_bot - pad
        line_range = 20

    def temp_to_y(temp):
        y = int((h - 1) * (1.0 - (temp - line_bot) / line_range))
        if y < 0:
            y = 0
        if y >= h:
            y = h - 1
        return y

    points = [(0, temp_to_y(temps[0]))]
    for i in range(1, n):
        x = (i * (w - 1)) // (n - 1) if n > 1 else 0
        points.append((x, temp_to_y(temps[i])))
    draw_aa_polyline(display, points, *COLOR_ORANGE, hw=1.25)

    display.show()
