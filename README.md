# pico-picture
Display system for Raspberry Pi Pico W

PicturePoster is a desktop app which translates standard image files into an http: PUT which
is received by the Pico W and displayed on the screen.

This is a "gateway" project to any desktop app which might compose pictures from whatever
sources (weather reports, home automation, calendar schedules, etc.) and make them appear
on the Pico screen wherever it may be (on the directly addressable network).

PicoWeather is an adaptation of PicturePoster which queries weather information from a (free)
[MeteoMatics](https://www.meteomatics.com/en/api/available-parameters/) API interface and
renders a weather info graphic that is PUT to the Pico screen.

Performance: approximately 0.3 frames per second.  Not intended for video applications.

pico-weather is a re-spin of the PicoWeather + image display server system, all-in-one
  system implemented on the PiPico alone without a remote process.  It is using OpenMeteo
  (meteomatics closed their free API, OpenMeteo doesn't require an api key.)

## pico-weather Install

### Prerequisites

1. Flash MicroPython firmware onto your Pico W:
   - Hold BOOTSEL while plugging in via USB
   - Drag `rp2-pico-w-latest.uf2` onto the drive that appears
2. Install mpremote on your PC: `pip install mpremote`

### Deploy to Pico W

1. Create your config file:
   ```bash
   cd pico-weather/pico
   cp config_example.json config.json
   ```
2. Edit `config.json` with your WiFi credentials and coordinates:
   ```json
   {
       "ssid": "YourNetworkName",
       "password": "YourNetworkPassword",
       "lat": 30.14,
       "lon": -81.55,
       "country": "US"
   }
   ```
3. Connect Pico W via USB and copy all files:
   ```bash
   python -m mpremote cp main.py weather.py renderer.py fonts.py display.py wifi.py config.json :
   ```
4. Reset the Pico to start: `python -m mpremote reset`

The device will connect to WiFi, fetch weather from Open-Meteo, and refresh every 5 minutes.

### Useful mpremote commands

- `python -m mpremote ls :` — list files on Pico
- `python -m mpremote repl` — interactive REPL
- `python -m mpremote run main.py` — run without copying
- `python -m mpremote reset` — soft-reset

### Desktop simulator

Run the tkinter simulator to preview the display without hardware:
```bash
cd pico-weather
pip install Pillow
python simulator.py [lat] [lon]
```

### Tests

```bash
cd pico-weather
pip install -r tests/requirements.txt
python -m pytest tests/ -v
```

Project Bill of Materials

- Raspberry Pi Pico W
- [Waveshare Pico LCD 1.14](https://www.waveshare.com/wiki/Pico-LCD-1.14#Overview)

Software Development

- Thonny for micropython development, seems to work better when installed using pip3 instead of apt
- [Official docs](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html#raspberry-pi-pico-w)
- [micropython](https://www.cnx-software.com/2022/07/03/getting-started-with-wifi-on-raspberry-pi-pico-w-board/#wifi-with-micropython) rp2-pico-w-latest.uf2 file for Pico W
- [flash_nuke.uf2](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html#resetting-flash-memory) file for Pico
- code obviously adapted from the Waveshare python example for the screen 
- and the Pico guide for http servers
