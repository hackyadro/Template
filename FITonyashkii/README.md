# FITonyashkii

## Запуск через Docker (Frontend + WebSocket)

Один контейнер запускает:

- Frontend (статические файлы из `public/`) на порту `2020`
- WebSocket/UDP сервер на порту `3030` (UDP по умолчанию `9999` внутри контейнера)

1. Соберите образ из корня репозитория:
   ```bash
   docker build -t fitonyashkii:latest .
   ```
2. Запустите контейнер, пробросив нужные порты:
   ```bash
   docker run --name fitonyashkii -p 2020:2020 -p 3030:3030 -p 9999:9999/udp fitonyashkii:latest
   ```

После запуска:

- Откройте интерфейс: http://localhost:2020

## Использование

- Веб-интерфейс (Docker) доступен: http://localhost:2020
- Основные файлы:
  - `server/server.py` — запуск сервера
  - `public/index.html`, `public/app.js`, `public/styles.css` — фронтенд
  - `server/rssi_locator.py`, `server/rssi_filter.py`, `server/solver.py` — логика обработки данных
  - `esp/main.py` — код для ESP32 (MicroPython) сканирования BLE и отправки RSSI по UDP

## Структура проекта

- `server/` — серверная часть (Python)
- `public/` — клиентская часть (HTML, JS, CSS)
- `esp/` — примеры для ESP
- `routes/` — сохранённые маршруты

## ESP32 (BLE сканер → UDP → сервер)

`esp/main.py` выполняет:
1. Подключение к Wi‑Fi
2. BLE сканирование (пассивное) длительной сессией
3. Парсинг рекламных пакетов (имя устройства, Tx Power, RSSI)
4. Отправку JSON по UDP на сервер

### Настройка

Отредактируйте в `esp/main.py`:
```python
WIFI_SSID = "YOUR_SSID"
WIFI_PASSWORD = "YOUR_PASSWORD"
SERVER_IP = "IP_СЕРВЕРА"      
SERVER_PORT = 9999
```

IP сервера:
- Если используете Docker локально: узнать IP хоста внутри LAN (не 127.0.0.1)
- Можно указать статический адрес машины где крутится контейнер

### Прошивка MicroPython

1. Скачайте последнюю прошивку MicroPython для ESP32: https://micropython.org/download/esp32/
2. Очистка и прошивка (пример, замените ttyUSB0 и имя файла):
   ```bash
   esptool.py --chip esp32 erase_flash
   esptool.py --chip esp32 write_flash -z 0x1000 micropython-ESP32.bin
   ```
3. Подключение REPL (опционально):
   ```bash
   screen /dev/ttyUSB0 115200
   ```

### Загрузка скрипта

Вариант через mpremote:
```bash
mpremote connect /dev/ttyUSB0 fs cp esp/main.py :main.py
mpremote connect /dev/ttyUSB0 reset
```

Или через ampy:
```bash
ampy -p /dev/ttyUSB0 put esp/main.py main.py
```


