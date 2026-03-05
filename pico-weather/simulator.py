"""PicoWeather Display Simulator

Opens a window showing exactly what the Waveshare LCD 1.14 will display.
Fetches live weather data from Open-Meteo and refreshes every 5 minutes,
matching the real device behavior.

The display is rendered at 240x135 native resolution and scaled up 4x
for comfortable viewing on a desktop monitor. A dark bezel surrounds the
display to approximate the physical LCD appearance.

Usage:
    python simulator.py [lat] [lon]

    Defaults to Austin, TX (30.27, -97.74) if no coordinates given.
    Press 'r' to force a refresh, 'q' or Escape to quit.
"""

import sys
import os
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw

# Add pico modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pico"))

import weather
import renderer

# Display geometry
LCD_W = 240
LCD_H = 135
SCALE = 4
BEZEL = 16  # pixels of dark bezel around display

UPDATE_MS = 300_000  # 5 minutes


class SimDisplay:
    """Display backend that renders into a Pillow image for the simulator."""

    def __init__(self):
        self.width = LCD_W
        self.height = LCD_H
        self.img = Image.new("RGB", (LCD_W, LCD_H), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)

    def fill(self, color):
        self.img = Image.new("RGB", (LCD_W, LCD_H), color)
        self.draw = ImageDraw.Draw(self.img)

    def pixel(self, x, y, color):
        if 0 <= x < LCD_W and 0 <= y < LCD_H:
            self.draw.point((x, y), fill=color)

    def line(self, x0, y0, x1, y1, color):
        self.draw.line([(x0, y0), (x1, y1)], fill=color)

    def hline(self, x, y, w, color):
        self.draw.line([(x, y), (x + w - 1, y)], fill=color)

    def vline(self, x, y, h, color):
        self.draw.line([(x, y), (x, y + h - 1)], fill=color)

    def fill_rect(self, x, y, w, h, color):
        self.draw.rectangle([x, y, x + w - 1, y + h - 1], fill=color)

    def add_pixel(self, x, y, r, g, b):
        """Draw pixel with additive blending against existing content."""
        if 0 <= x < LCD_W and 0 <= y < LCD_H:
            bg = self.img.getpixel((x, y))
            nr = min(bg[0] + r, 255)
            ng = min(bg[1] + g, 255)
            nb = min(bg[2] + b, 255)
            self.draw.point((x, y), fill=(nr, ng, nb))

    def blend_pixel(self, x, y, r, g, b, a):
        """Draw pixel alpha-blended with existing content. a: 0-255."""
        if 0 <= x < LCD_W and 0 <= y < LCD_H:
            if a >= 255:
                self.draw.point((x, y), fill=(r, g, b))
                return
            if a <= 0:
                return
            bg = self.img.getpixel((x, y))
            inv = 255 - a
            nr = (bg[0] * inv + r * a + 127) // 255
            ng = (bg[1] * inv + g * a + 127) // 255
            nb = (bg[2] * inv + b * a + 127) // 255
            self.draw.point((x, y), fill=(nr, ng, nb))

    def text(self, string, x, y, color):
        self.draw.text((x, y), string, fill=color)

    def show(self):
        pass  # Handled by the simulator's refresh loop


class Simulator:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.display = SimDisplay()
        self.last_ranges = None
        self.update_id = None

        # Window setup
        win_w = LCD_W * SCALE + BEZEL * 2
        win_h = LCD_H * SCALE + BEZEL * 2

        self.root = tk.Tk()
        self.root.title("PicoWeather Simulator  [{}, {}]".format(lat, lon))
        self.root.configure(bg="#1a1a1a")
        self.root.resizable(False, False)

        # Outer frame simulates the PCB / device body
        frame = tk.Frame(self.root, bg="#2a2a2a", padx=BEZEL, pady=BEZEL)
        frame.pack()

        # Canvas for the LCD display area
        self.canvas = tk.Canvas(frame, width=LCD_W * SCALE,
                                height=LCD_H * SCALE,
                                bg="black", highlightthickness=0)
        self.canvas.pack()

        # Status bar below the display
        self.status_var = tk.StringVar(value="Starting...")
        status = tk.Label(self.root, textvariable=self.status_var,
                          bg="#1a1a1a", fg="#888888",
                          font=("Consolas", 9), anchor="w")
        status.pack(fill="x", padx=BEZEL)

        # Key bindings
        self.root.bind("<Key-r>", lambda e: self.refresh())
        self.root.bind("<Key-q>", lambda e: self.root.destroy())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # Kick off first update
        self.root.after(100, self.refresh)

    def refresh(self):
        """Fetch weather data and re-render the display."""
        if self.update_id is not None:
            self.root.after_cancel(self.update_id)

        self.status_var.set("Fetching weather data...")
        self.root.update_idletasks()

        wd = weather.fetch_weather(self.lat, self.lon)
        if wd is not None:
            ranges = weather.compute_ranges(wd)
            if ranges is not None:
                self.last_ranges = ranges

        if self.last_ranges is not None:
            renderer.render_weather(self.display, self.last_ranges)
            r = self.last_ranges
            self.status_var.set(
                "Now: {:.0f}F  Range: {:.0f}-{:.0f}F  "
                "Precip max: {:.1f}mm  |  "
                "Press 'r' to refresh, 'q' to quit".format(
                    r["current_temp"], r["min_temp"], r["max_temp"],
                    max(r["precipitations"])))
        else:
            # Show error state
            self.display.fill((0, 0, 0))
            self.display.text("No data", 80, 60, (255, 80, 80))
            self.status_var.set(
                "Failed to fetch weather data  |  Press 'r' to retry")

        self._update_canvas()

        # Schedule next refresh
        self.update_id = self.root.after(UPDATE_MS, self.refresh)

    def _update_canvas(self):
        """Scale the display image and draw it on the canvas."""
        scaled = self.display.img.resize(
            (LCD_W * SCALE, LCD_H * SCALE), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(scaled)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

    def run(self):
        self.root.mainloop()


def main():
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 30.27
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else -97.74
    sim = Simulator(lat, lon)
    sim.run()


if __name__ == "__main__":
    main()
