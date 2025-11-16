from machine import Pin,SPI,PWM
import framebuf
import time
from time import sleep
import network
import socket
from rp2 import country
import sys

# Load configuration
try:
    import config
except ImportError:
    print("ERROR: config.py not found!")
    print("Copy config.py.template to config.py and update with your WiFi credentials")
    sys.exit(1)

# Hardware pin configuration
BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

# Display constants
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135
BUFFER_SIZE = SCREEN_WIDTH * SCREEN_HEIGHT * 2  # RGB565 = 2 bytes per pixel

# Correct RGB565 color values (5-6-5 bit format: RRRRR GGGGGG BBBBB)
RED   = 0xF800  # 11111 000000 00000
GREEN = 0x07E0  # 00000 111111 00000
BLUE  = 0x001F  # 00000 000000 11111
WHITE = 0xFFFF  # 11111 111111 11111
BLACK = 0x0000  # 00000 000000 00000
ORANGE = 0xFD20 # 11111 101001 00000

class LCD_1inch14(framebuf.FrameBuffer):
    def __init__(self):
        self.done = False
        self.BLduty = 32768
        self.pwm = PWM(Pin(BL))
        self.pwm.freq(1000)
        self.pwm.duty_u16(self.BLduty) #max 65535
        
        self.width = 240
        self.height = 135
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,1000_000)
        self.spi = SPI(1,10000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()

        # Use module-level color constants
        self.red = RED
        self.green = GREEN
        self.blue = BLUE
        self.white = WHITE
        self.black = BLACK
        self.orange = ORANGE
        
    def handleBacklight( self, request ):
        if len(request) > 21:
            if 6 == request.find('/backlight'):
                self.BLduty = int(request[16:21])
                if ( self.BLduty < 0 ):
                    self.BLduty = 0
                if ( self.BLduty > 65535 ):
                    self.BLduty = 65535                
                self.pwm.duty_u16(self.BLduty)

    def handleGet( self, request, cl ):
        if ( 6 == request.find('/favicon.ico') ):
            cl.send('HTTP/1.0 200 OK\r\nContent-type: image/x-icon\r\nContent-length: 0\r\n\r\n')
            cl.close()
        else:
            handleBacklight( self, request )
            if 6 == request.find('/exit'):
                self.done = True
                
            html = """<!DOCTYPE html>
            <html> <head> <title>pico-picture</title> </head>
                <body> <h1>pico-picture</h1>
                    Do an http PUT with a body of 240x135 565 RGB values
                    to put that image on the display.<br/>
                    The <a href="https://github.com/MangoCats/pico-picture">Picture Poster</a>
                    application demonstrates how.
                    <hr/>{}
                </body>
            </html>
            """
            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            cl.send( html.format( request ) )
            cl.close()
            
            self.text( request[2:28], 20, 50, LCD.black )
            self.show()
            
# def handleGet()

    def handlePut(self, request, cl):
        """Handle HTTP PUT request to update display image.

        Expected: 64,800 bytes of RGB565 pixel data (240x135x2)
        Format: Little-endian RGB565 (RRRRR GGGGGG BBBBB)
        """
        print(request)
        handleBacklight(self, request)

        # Read image data with size validation
        try:
            body = cl.read(BUFFER_SIZE)

            # Validate buffer size
            if len(body) != BUFFER_SIZE:
                error_msg = 'HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nInvalid image size: expected {} bytes, got {}\r\n'.format(BUFFER_SIZE, len(body))
                cl.send(error_msg)
                cl.close()
                print("ERROR: Invalid PUT size:", len(body))
                return

            # Direct buffer copy - fast update
            self.buffer[:] = body
            self.show()

            # Success response
            cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK')

        except Exception as e:
            print("ERROR in handlePut:", e)
            try:
                cl.send('HTTP/1.1 500 Internal Server Error\r\n\r\n')
            except:
                pass
        finally:
            try:
                cl.close()
            except:
                pass
            
# def handleGet()

    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize display (ST7789 controller)"""  
        self.rst(1)
        self.rst(0)
        self.rst(1)
        
        self.write_cmd(0x36)
        self.write_data(0x70)

        self.write_cmd(0x3A) 
        self.write_data(0x05)

        self.write_cmd(0xB2)
        self.write_data(0x0C)
        self.write_data(0x0C)
        self.write_data(0x00)
        self.write_data(0x33)
        self.write_data(0x33)

        self.write_cmd(0xB7)
        self.write_data(0x35) 

        self.write_cmd(0xBB)
        self.write_data(0x19)

        self.write_cmd(0xC0)
        self.write_data(0x2C)

        self.write_cmd(0xC2)
        self.write_data(0x01)

        self.write_cmd(0xC3)
        self.write_data(0x12)   

        self.write_cmd(0xC4)
        self.write_data(0x20)

        self.write_cmd(0xC6)
        self.write_data(0x0F) 

        self.write_cmd(0xD0)
        self.write_data(0xA4)
        self.write_data(0xA1)

        self.write_cmd(0xE0)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0D)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2B)
        self.write_data(0x3F)
        self.write_data(0x54)
        self.write_data(0x4C)
        self.write_data(0x18)
        self.write_data(0x0D)
        self.write_data(0x0B)
        self.write_data(0x1F)
        self.write_data(0x23)

        self.write_cmd(0xE1)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0C)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2C)
        self.write_data(0x3F)
        self.write_data(0x44)
        self.write_data(0x51)
        self.write_data(0x2F)
        self.write_data(0x1F)
        self.write_data(0x1F)
        self.write_data(0x20)
        self.write_data(0x23)
        
        self.write_cmd(0x21)

        self.write_cmd(0x11)

        self.write_cmd(0x29)

    def show(self):
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x28)
        self.write_data(0x01)
        self.write_data(0x17)
        
        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x35)
        self.write_data(0x00)
        self.write_data(0xBB)
        
        self.write_cmd(0x2C)
        
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)
  
if __name__=='__main__':

    # Select the onboard LED
    led = machine.Pin("LED", machine.Pin.OUT)
    led.value(1)  # LED stays on until WiFi is connected

    # Set country code from config
    wifi_country = getattr(config, 'WIFI_COUNTRY', 'US')
    country(wifi_country)

    # Initialize display
    LCD = LCD_1inch14()

    # Draw border on startup
    LCD.fill(LCD.white)
    LCD.show()

    LCD.hline(10, 10, 220, LCD.blue)
    LCD.hline(10, 125, 220, LCD.blue)
    LCD.vline(10, 10, 115, LCD.blue)
    LCD.vline(230, 10, 115, LCD.blue)
    LCD.show()

    # Setup button for manual exit (center button)
    key3 = Pin(3, Pin.IN, Pin.PULL_UP)

    # Load WiFi credentials from config
    ssid = config.WIFI_SSID
    password = config.WIFI_PASSWORD

    print("WiFi connection starting")
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect( ssid, password )

# Wait for connect or fail
    max_wait = 25
    while max_wait > 0:
      if wlan.status() < 0 or wlan.status() >= 3:
        break
      max_wait -= 1
      msg = 'waiting ' + str(max_wait)
      LCD.fill_rect( 19, 19, 211, 10, LCD.white )        
      LCD.text( msg, 20, 20, LCD.black )
      LCD.show()
      sleep(1)
  
    # Handle connection error
    if wlan.status() != 3:
        raise RuntimeError('WiFi connection failed')
    else:
        status = wlan.ifconfig()
        LCD.fill_rect(19, 19, 211, 10, LCD.white)
        LCD.text(wlan.config('essid'), 20, 20, LCD.black)
        LCD.text(status[0], 20, 30, LCD.black)
        LCD.show()
        led.value(0)

    # Open HTTP server socket
    http_port = getattr(config, 'HTTP_PORT', 80)
    addr = socket.getaddrinfo('0.0.0.0', http_port)[0][-1]

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print('HTTP server listening on', addr)

    LCD.done = False
    error_count = 0
    max_errors = 10

    while not LCD.done:
        cl = None
        try:
            # Check for manual exit button
            if key3.value() == 0:
                print("Exit by button press")
                LCD.text("Exit by Button Press", 20, 55, LCD.black)
                LCD.done = True
                break

            # Accept connection with timeout
            s.settimeout(1.0)
            try:
                cl, client_addr = s.accept()
            except OSError:
                continue  # Timeout, check exit button again

            # Read request with bounds checking
            request_bytes = cl.recv(2048)
            if not request_bytes:
                continue

            request = str(request_bytes)

            # Display client address
            LCD.fill_rect(19, 39, 211, 20, LCD.white)
            LCD.text(' '.join(map(str, client_addr)), 20, 40, LCD.black)

            # Parse HTTP method safely
            if len(request) > 5:
                # Extract method from request line
                try:
                    # Request format: b'METHOD /path HTTP/1.1\r\n...'
                    method_end = request.find(' ', 2)
                    if method_end > 2:
                        method = request[2:method_end]

                        if method == "GET":
                            LCD.handleGet(request, cl)
                        elif method == "PUT":
                            LCD.handlePut(request, cl)
                        else:
                            cl.send('HTTP/1.1 405 Method Not Allowed\r\n\r\n')
                            cl.close()
                except Exception as e:
                    print("Request parse error:", e)
                    try:
                        cl.send('HTTP/1.1 400 Bad Request\r\n\r\n')
                        cl.close()
                    except:
                        pass

            # Reset error count on successful request
            error_count = 0

        except OSError as e:
            print('Connection error:', e)
            error_count += 1

            if error_count >= max_errors:
                print('Too many errors, restarting server...')
                try:
                    s.close()
                except:
                    pass

                # Recreate socket
                s = socket.socket()
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(addr)
                s.listen(1)
                error_count = 0

        except Exception as e:
            print('Unexpected error:', e)
            error_count += 1

        finally:
            # Always close client socket
            if cl:
                try:
                    cl.close()
                except:
                    pass

    # Cleanup
    print("Shutting down...")
    try:
        s.close()
    except:
        pass

    LCD.fill_rect(12, 19, 217, 20, LCD.blue)
    LCD.show()
    print("DONE")
