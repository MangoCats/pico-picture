from machine import Pin,SPI,PWM
import framebuf
import time
from time import sleep
import network
import socket
from rp2 import country

BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

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
        
        self.red   =   0x07E0  # 0x00E0 looks similar
        self.green =   0x001F  # 0x0007 looks similar
        self.blue  =   0xF800  # 0x3800 looks similar
        self.white =   0xFFFF
        self.black  =  0x0000
        self.orange =  0x07ED
        
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

    def handlePut( self, request, cl ):
        print(request)
        handleBacklight( self, request )
        msg = "PUT " + str( len(request) )
        self.text( msg, 20, 50, LCD.black )
        self.show()
        body = cl.read(64800)
        i = 1
        y = 0
        x = 0
        while ( i < len(body) - 1 ):
          c = body[i] + body[i+1] * 256
          i += 2
          if ( y < 135 ):
            self.pixel( x, y, c )
          x += 1
          if ( x >= 240 ):
            x = 0
            y += 1            
        self.show()
              
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\nContent-length: 0\r\n\r\n')
        cl.close()
            
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
        """Initialize dispaly"""  
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
    led.value(1) # LED stays on until WiFi is connected
# Set country code, opens legal WiFi channels
    country('US')
    
    LCD = LCD_1inch14()
    
#color BRG
    LCD.fill(LCD.white)
 
    LCD.show()
    
    LCD.hline( 10, 10,220,LCD.blue)
    LCD.hline( 10,125,220,LCD.blue)
    LCD.vline( 10, 10,115,LCD.blue)
    LCD.vline(230, 10,115,LCD.blue)
    
    LCD.show()
    keyA = Pin(15,Pin.IN,Pin.PULL_UP)
    keyB = Pin(17,Pin.IN,Pin.PULL_UP)
    
    key2 = Pin( 2,Pin.IN,Pin.PULL_UP) #???
    key3 = Pin( 3,Pin.IN,Pin.PULL_UP) #???
    key4 = Pin(16,Pin.IN,Pin.PULL_UP) #???
    key5 = Pin(18,Pin.IN,Pin.PULL_UP) #???
    key6 = Pin(20,Pin.IN,Pin.PULL_UP) #???
    
    ssid     = 'Imnot'
    password = 'telling'

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
      raise RuntimeError('network connection failed')
    else:
      status = wlan.ifconfig()
      LCD.fill_rect( 19, 19, 211, 10, LCD.white )        
      LCD.text( wlan.config('essid'),20,20,LCD.black )
      LCD.text( status[0]           ,20,30,LCD.black )
      LCD.show()
      led.value(0)
      
# Open socket
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print('listening on', addr)
    
    LCD.done = False
    while LCD.done == False:
        try:
            cl, addr = s.accept()
            request = str( cl.recv(2048) )
            
            # Erase text lines 3 & 4
            LCD.fill_rect( 19, 39, 211, 20, LCD.white )
            LCD.text( ' '.join(map(str, addr)), 20, 40, LCD.black )

            if (key3.value() == 0):
                LCD.text( "Exit by Button Press", 20, 55, LCD.black )
                LCD.done = True
            elif len(request) > 5:
                if ( request[2:5] == "GET" ):
                    LCD.handleGet( request, cl )
                elif ( request[2:5] == "PUT" ):
                    LCD.handlePut( request, cl )
                
            cl.close()
                    
        except OSError as e:
            cl.close()
            print('connection closed')

    # while !done    
    print("DONE")
    s.close()
    LCD.fill_rect( 12, 19, 217, 20, LCD.blue )        
    LCD.show()
