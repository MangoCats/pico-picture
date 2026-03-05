"""Desktop display backend using Pillow for testing."""

from PIL import Image, ImageDraw


class DesktopDisplay:
    WIDTH = 240
    HEIGHT = 135

    def __init__(self):
        self.img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)

    def fill(self, color):
        self.img = Image.new("RGB", (self.WIDTH, self.HEIGHT), color)
        self.draw = ImageDraw.Draw(self.img)

    def pixel(self, x, y, color):
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
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
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            bg = self.img.getpixel((x, y))
            nr = min(bg[0] + r, 255)
            ng = min(bg[1] + g, 255)
            nb = min(bg[2] + b, 255)
            self.draw.point((x, y), fill=(nr, ng, nb))

    def blend_pixel(self, x, y, r, g, b, a):
        """Draw pixel alpha-blended with existing content. a: 0-255."""
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
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
        pass  # No-op on desktop

    def save(self, path="output.png"):
        self.img.save(path)
