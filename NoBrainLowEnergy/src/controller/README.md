# NoBrainLowEnergy controller

## Prerequisites

- esptool for flashing esp32 `pip install esptool`
- mpremote `pip install mpremote` (or any other way to transfer file to the micropython installation)

## Instruction

1) download micropython firmware for esp32-s3 from https://micropython.org/download/ESP32_GENERIC_S3/
2) connect esp32 via usb port labeled COM
3) execute `esptool erase-flash`
4) execute `esptool write-flash <path-to-downloaded-firmware>`
5) use mpremote to transfer files:
   1) `mpremote fs cp main.py :/main.py`
   2) `mpremote fs cp boot.py :/boot.py`
   3) configurate the mqtt_config.json with the wifi access point info and mqtt ip address and port
   4) upload config `mpremote fs cp mqtt_config.json :/mqtt_config.json`
6) reset the controller via button or sending `ctrl+D` after connecting via `mpremote connect <com-port>`
