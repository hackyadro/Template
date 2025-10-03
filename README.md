# CR7 — Indoor Positioning (BLE → RSSI → Trilateration)

Система позиционирования в помещении: ESP32 сканирует BLE-устройства и публикует их RSSI в MQTT; бэкенд агрегирует и вычисляет координаты, фронтенд отображает карту, маяки и текущую позицию.

## Быстрый запуск (Docker Compose)

Требования: Docker, Docker Compose.

```sh
# из корня репозитория
docker compose -f CR7/CR7/docker-compose.yml up -d --build
```

После запуска:
- Фронтенд: http://localhost:3000
- Бэкенд API: http://localhost:3277
- MQTT брокер: tcp://localhost:1883 (конфиг: [CR7/CR7/mosquitto/mosquitto.conf](CR7/CR7/mosquitto/mosquitto.conf))

ESP32 указывает адрес брокера через `MQTT_SERVER` в [CR7/CR7/esp32/main.py](CR7/CR7/esp32/main.py). В Docker-сети бэкенд подключается к хосту `mosquitto` (см. [`config.MQTT_SERVER`](CR7/CR7/backend/config.py)).

## Локальный запуск (без Docker)

1) MQTT брокер  
- Вариант A (локально): установить Mosquitto и запустить на 1883.  
- Вариант B (в контейнере):  
  ```sh
  docker run -it --rm -p 1883:1883 -v "$PWD/CR7/CR7/mosquitto/mosquitto.conf":/mosquitto/config/mosquitto.conf eclipse-mosquitto
  ```

2) Бэкенд (Flask + MQTT)
```sh
cd CR7/CR7/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# при локальном брокере смените хост на "localhost" в [`config.MQTT_SERVER`](CR7/CR7/backend/config.py)
python main.py
```

3) Фронтенд (Nuxt 3)
```sh
cd CR7/CR7/frontend
pnpm i   # или npm i
pnpm dev # http://localhost:3000
```
По умолчанию фронтенд проксирует запросы `/api/*` на http://backend:3277 (см. [CR7/CR7/frontend/nuxt.config.ts](CR7/CR7/frontend/nuxt.config.ts)). Для локальной разработки укажите прокси на http://localhost:3277.

4) ESP32  
Прошейте устройства кодом [CR7/CR7/esp32/main.py](CR7/CR7/esp32/main.py), укажите корректные `WIFI_SSID`, `WIFI_PASS`, `MQTT_SERVER` (IP брокера). Устройство публикует JSON в топик `beacons`.

## Как пользоваться

- Откройте фронтенд (http://localhost:3000). На канвасе отображаются:
  - синие точки — маяки из файла `standart.beacons`;
  - красная точка — текущая позиция;
  - зелёная линия — записанный маршрут.
- Кнопкой «Начать/Завершить путь» можно записать трек; при завершении он сохраняется в файл `sol.path` (CSV `X;Y`) — экспорт реализован на странице [CR7/CR7/frontend/app/pages/index.vue](CR7/CR7/frontend/app/pages/index.vue).
- Бэкенд выдаёт:
  - GET `/api/position` → текущие координаты и метрики;
  - GET `/api/beacons` → словарь маяков.
  Эндпоинты объявлены в [CR7/CR7/backend/api.py](CR7/CR7/backend/api.py) (см. [`api.run_api`](CR7/CR7/backend/api.py)).

