# Yadronshiki Indoor	 Project

## Что реализовано
- **device/** — код для ESP32-S3 на Micropython (сканирует BLE-маяки и шлёт их в MQTT).
- **scripts/locator.py** — скрипт, который подписывается на MQTT и пишет координаты приёмника в `standart.path`.
- **docker-compose.yml** — поднимает MQTT брокер + скрипт-локатор.
- **standart.beacons** — входные данные с координатами маяков.
- **standart.path** — выходные данные с рассчитанными координатами приёмника.

## Прошивка микроконтроллера 
В папке `bin/` лежит файл `firmware.bin` — это готовая прошивка для микроконтроллера.

### Требования
- Установить Python 3.9+
- Установить `esptool`:
  ```bash
  pip install esptool

### Прошивка
1. Определите порт к которому подключен приемник, к примеру COM3
2. Стерите существующую прошивку с приемника если она есть
  ```bash
  esptool.py --chip esp32s3 --port COM3 erase_flash
3. Прошейте приемник
  ```bash
  esptool.py --chip esp32s3 --port YOUR-PORT --baud 460800 write_flash -z 0x0 PATH-TO-FRIMWARE	   	

## Запуск
1. Установите Docker и Docker Compose.
2. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/Oli1331/Yadronshiki.git
   cd yadronshiki
3. Запустите систему
   ```bash
   docker compose up --build
4. Устройство ESP32-S3 должно быть прошито кодом из device/main.py и подключено к Wi-Fi.
Оно будет публиковать данные в MQTT-брокер (beacons/discovered) 
