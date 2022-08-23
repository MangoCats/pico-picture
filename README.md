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
