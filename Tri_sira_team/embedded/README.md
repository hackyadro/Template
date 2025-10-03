# ESP32 BLE RSSI Tracker with Triangulation

Проект на MicroPython для ESP32, который собирает RSSI-сигналы от BLE-маяков, вычисляет расстояние и позицию устройства с использованием триангуляции. Данные публикуются на MQTT-брокер.

---

## Функционал

- Сбор BLE RSSI с нескольких маяков
- Сглаживание RSSI с помощью EMA и фильтра Калмана
- Отправка данных на MQTT-брокер
- LED-индикация каждого измерения

---
## Требования

- ESP32    
- MicroPython
- Python 3.7+
- MQTT-брокер
- BLE-маяки
    

---

## Подготовка платы

1. **Установите MicroPython на ESP32**  
    Скачайте прошивку с официального сайта [MicroPython ESP32](https://micropython.org/download/esp32/).  
    Затем прошейте плату через `esptool.py`:
    
    ```bash
    pip install esptool
    esptool.py --chip esp32 erase_flash
    esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-20230926-v1.21.1.bin
    ```
    
2. **Установите `mpremote`**
    
    ```bash
    pip install mpremote
    ```
    
3. **Подключите ESP32 к компьютеру** и проверьте порт:
    
    ```bash
    mpremote list
    ```
    

---

## Настройка `secrets.py`

Создайте файл `secrets.py` с вашими данными:

```python
secrets = {
    "ssid": "YOUR_WIFI_SSID",
    "password": "YOUR_WIFI_PASSWORD"
}

mqtt_env = {
    "broker": "mqtt.example.com",
    "port": 1883,
    "username": "mqtt_user",
    "password": "mqtt_pass",
    "topic": "esp32/rssi"
}

TARGET_BEACONS = {
    "beacon_1": "AA:BB:CC:DD:EE:01",
    "beacon_2": "AA:BB:CC:DD:EE:02",
    "beacon_3": "AA:BB:CC:DD:EE:03",
    "beacon_7": "AA:BB:CC:DD:EE:07"
}
```

---

## Запуск

1. Подключитесь к ESP32:
    

```bash
mpremote connect /dev/ttyUSB0
```
2. добавьте secrets.py и KalmanFilter.py esp.py на плату: 
```bash
mpremote connect /dev/ttyUSB0 cp secrets.py :
mpremote connect /dev/ttyUSB0 cp KalmanFilter.py :
mpremote connect /dev/ttyUSB0 cp esp.py :
``` 
2. Запустите скрипт:
    

```bash
mpremote run esp.py
```

---

## MQTT

Скрипт публикует данные в формате JSON:

```json
{
    "beacon_name": "beacon_1",
    "avg_rssi": -57.25,
    "tx_power": -43
}
```

