esptool --port /dev/ttyUSB0 erase_flash
esptool --port=/dev/ttyUSB0 --baud 460800 write_flash 0x0 ESP32_GENERIC_S3-SPIRAM_OCT-20250911-v1.26.1.bin