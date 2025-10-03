Этот проект позволяет использовать **ESP32** как считыватель BLE-маяков и отправлять данные о сигнале (**RSSI**) на сервер через **MQTT**.

---
### Требования
- ESP32 (с поддержкой Wi-Fi и Bluetooth)
- Thonny IDE (Python IDE с поддержкой MicroPython)
- Прошивка **MicroPython** на ESP32 (официальный сайт)
- MQTT-брокер (например, Mosquitto, EMQX или встроенный в Home Assistant)
---

## Установка прошивки на ESP32

1. Скачайте **MicroPython прошивку** для ESP32:  
    [MicroPython - Python for microcontrollers](https://micropython.org/download/ESP32_GENERIC/)
2. Установите утилиту `esptool.py` (если ещё не установлена):
    `pip install esptool`
3. Подключите ESP32 к компьютеру и прошейте:
    `esptool.py --chip esp32 --port COM7 erase_flash esptool.py --chip esp32 --port COM7 write_flash -z 0x1000 esp32-[версия].bin`
    
    ⚠️ Замените `COM7` на ваш порт и `esp32-[версия].bin` на скачанный файл.
    

---

## Загрузка и запуск кода в Thonny

1. Установите **Thonny**: thonny.org
2. Подключите ESP32 и выберите его порт:
    - В Thonny: `Инструменты → Настройки → Интерпретатор → MicroPython (ESP32)`
3. Скопируйте файлы на плату:
    - `esp32.py`
    - `config_esp32.py`
4. Нажмите **Run **для запуска `esp32.py`.
    

---

## Настройка `config_esp32.py`

Откройте файл `config_esp32.py` и укажите свои параметры:

MQTT_BROKER = "192.168.3.26"   # IP брокера
MQTT_PORT = 1883
MQTT_TOPIC = "beacons/rssi"
CLIENT_ID = "beacon_publisher_01"

WIFI_SSID = "ваш_вайфай"
WIFI_PASSWORD = "ваш_пароль"

SCAN_DURATION_MS = 1000  # время одного скана (мс)
SCAN_INTERVAL = 1        # пауза между циклами (сек)
SCAN_FREQ = 100          # частота проверки статуса (мс)

BEACON_PREFIX = "beacon_"  # фильтрация по имени маяка

---

## Как работает `esp32.py`

- Подключается к Wi-Fi (данные берутся из `config_esp32.py`).
- Запускает Bluetooth-сканер и ищет устройства, начинающиеся с `BEACON_PREFIX`.
- Собирает **RSSI** для найденных маяков.
- Отправляет результат в MQTT-брокер в JSON-формате.

Пример данных, отправляемых в топик:

`[["beacon_1", -45], ["beacon_2", -67]]`

Если маяки не найдены:

`"NO_BEACONS_FOUND"`

---

## Проверка работы

1. Запустите MQTT-брокер (например, Mosquitto).
2. Подпишитесь на топик:
    `mosquitto_sub -h 192.168.3.26 -t beacons/rssi`
3. Должны приходить данные в реальном времени:
    `[["beacon_maxim", -34], ["beacon_matvey", -45]]`
---

##  Возможные ошибки

-  **"Не удалось подключиться к Wi-Fi"** → Проверьте SSID и пароль.
    
-  **"Ошибка публикации"** → Проверьте IP MQTT-брокера и его доступность.
    
-  **Нет маяков** → Убедитесь, что у маяков имя начинается с `BEACON_PREFIX`.
    

---
