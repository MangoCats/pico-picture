# display.py - Waveshare Pico LCD 1.14 hardware driver
# Adapted from pico-picture.py LCD_1inch14 class
# Hardware-dependent: requires MicroPython machine and framebuf modules

from machine import Pin, SPI, PWM
import framebuf
import time

# Pin assignments for Waveshare Pico LCD 1.14
PIN_BL = 13    # Backlight (PWM)
PIN_DC = 8     # Data/Command
PIN_RST = 12   # Reset
PIN_MOSI = 11  # SPI MOSI
PIN_SCK = 10   # SPI Clock
PIN_CS = 9     # Chip Select

WIDTH = 240
HEIGHT = 135


class PicoDisplay(framebuf.FrameBuffer):
    def __init__(self):
        self.width = WIDTH
        self.height = HEIGHT

        # Backlight PWM
        self.pwm = PWM(Pin(PIN_BL))
        self.pwm.freq(1000)
        self.pwm.duty_u16(32768)

        # SPI and control pins
        self.cs = Pin(PIN_CS, Pin.OUT)
        self.rst = Pin(PIN_RST, Pin.OUT)
        self.dc = Pin(PIN_DC, Pin.OUT)

        self.cs(1)
        self.dc(1)
        self.spi = SPI(1, 10_000_000, polarity=0, phase=0,
                       sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI), miso=None)

        # Framebuffer
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)

        self._init_display()

    def _write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def _write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def _init_display(self):
        self.rst(1)
        time.sleep_ms(10)
        self.rst(0)
        time.sleep_ms(10)
        self.rst(1)
        time.sleep_ms(10)

        self._write_cmd(0x36); self._write_data(0x70)
        self._write_cmd(0x3A); self._write_data(0x05)

        self._write_cmd(0xB2)
        for b in [0x0C, 0x0C, 0x00, 0x33, 0x33]:
            self._write_data(b)

        self._write_cmd(0xB7); self._write_data(0x35)
        self._write_cmd(0xBB); self._write_data(0x19)
        self._write_cmd(0xC0); self._write_data(0x2C)
        self._write_cmd(0xC2); self._write_data(0x01)
        self._write_cmd(0xC3); self._write_data(0x12)
        self._write_cmd(0xC4); self._write_data(0x20)
        self._write_cmd(0xC6); self._write_data(0x0F)

        self._write_cmd(0xD0)
        self._write_data(0xA4); self._write_data(0xA1)

        self._write_cmd(0xE0)
        for b in [0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F,
                  0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23]:
            self._write_data(b)

        self._write_cmd(0xE1)
        for b in [0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F,
                  0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23]:
            self._write_data(b)

        self._write_cmd(0x21)  # Display inversion on
        self._write_cmd(0x11)  # Sleep out
        self._write_cmd(0x29)  # Display on

    def show(self):
        """Flush framebuffer to LCD."""
        self._write_cmd(0x2A)
        self._write_data(0x00); self._write_data(0x28)
        self._write_data(0x01); self._write_data(0x17)

        self._write_cmd(0x2B)
        self._write_data(0x00); self._write_data(0x35)
        self._write_data(0x00); self._write_data(0xBB)

        self._write_cmd(0x2C)

        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

    def set_backlight(self, duty):
        """Set backlight brightness (0-65535)."""
        if duty < 0:
            duty = 0
        if duty > 65535:
            duty = 65535
        self.pwm.duty_u16(duty)

    def _read_rgb(self, offset):
        """Read RGB888 from framebuffer at byte offset (handles byte-swap)."""
        lo = self.buffer[offset]
        hi = self.buffer[offset + 1]
        # Undo byte-swap: buffer stores swapped bytes
        val = (lo << 8) | hi
        return (val >> 11) << 3, ((val >> 5) & 0x3F) << 2, (val & 0x1F) << 3

    def add_pixel(self, x, y, r, g, b):
        """Draw pixel with additive blending against existing framebuffer content."""
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 2
            br, bg, bb = self._read_rgb(offset)
            nr = min(br + r, 255)
            ng = min(bg + g, 255)
            nb = min(bb + b, 255)
            self.pixel(x, y, self.rgb565(nr, ng, nb))

    def blend_pixel(self, x, y, r, g, b, a):
        """Draw pixel alpha-blended with existing framebuffer content. a: 0-255."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if a >= 255:
                self.pixel(x, y, self.rgb565(r, g, b))
                return
            if a <= 0:
                return
            offset = (y * self.width + x) * 2
            br, bg, bb = self._read_rgb(offset)
            inv = 255 - a
            nr = (br * inv + r * a) // 255
            ng = (bg * inv + g * a) // 255
            nb = (bb * inv + b * a) // 255
            self.pixel(x, y, self.rgb565(nr, ng, nb))

    @staticmethod
    def rgb565(r, g, b):
        """Convert RGB888 to RGB565 with byte-swap for ST7789 big-endian SPI."""
        r5 = r >> 3
        g6 = g >> 2
        b5 = b >> 3
        p = (r5 << 11) | (g6 << 5) | b5
        # Swap bytes: framebuf stores LE uint16, ST7789 reads BE over SPI
        return ((p & 0xFF) << 8) | (p >> 8)
