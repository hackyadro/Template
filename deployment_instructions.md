CR7 — Инструкция по развертыванию на Linux

Эта инструкция подойдёт для Ubuntu/Debian. Предполагается, что папка проекта уже есть на диске.

Docker Compose 

Требования:
- Docker Engine + Docker Compose Plugin


Подключение ESP32

- Прошейте MicroPython на ESP32.
- Отредактируйте CR7/CR7/esp32/main.py: WIFI_SSID, WIFI_PASS, MQTT_SERVER (IP вашего ПК), MQTT_PORT, MQTT_TOPIC.
- Загрузите файл:
```bash
pip install -U mpremote
mpremote connect auto fs cp CR7/CR7/esp32/main.py :main.py
```
ESP32 начнёт публиковать JSON в топик "beacons".

Запуск:
```bash
cd /path/to/your/repo
docker compose -f docker-compose.yml up -d --build
```

Что поднимется:
- Frontend (Nuxt): http://localhost:3000
- Backend (API): http://localhost:3277
- MQTT брокер (Mosquitto): tcp://localhost:1883

MQTT_SERVER в контейнерном бэкенде — "mosquitto" (внутрисетевая DNS-имя сервиса).

Логи/управление:
```bash
docker compose -f CR7/CR7/docker-compose.yml logs -f backend
docker compose -f CR7/CR7/docker-compose.yml logs -f frontend
docker compose -f CR7/CR7/docker-compose.yml logs -f mosquitto
docker compose -f CR7/CR7/docker-compose.yml restart
docker compose -f CR7/CR7/docker-compose.yml down
```

Обновление после изменений:
```bash
docker compose -f CR7/CR7/docker-compose.yml up -d --build --force-recreate
```

