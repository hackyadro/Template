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

### Тест без железа (публикация RSSI вручную)
```sh
mosquitto_pub -h localhost -t beacons -m '{"name":"beacon_1","rssi":-70}'
```
Парсер MQTT: [`mqtt_handler.on_message`](CR7/CR7/backend/mqtt_handler.py). Бэкенд принимает JSON `{"name":"<beacon>","rssi":<int|float>}` и сглаживает по окну времени (см. [`mqtt_handler.get_smoothed_rssi`](CR7/CR7/backend/mqtt_handler.py), [`config.WINDOW_SEC`](CR7/CR7/backend/config.py)).

## Структура репозитория

- [CR7/CR7](CR7/CR7) — корень приложений и конфигураций
  - [docker-compose.yml](CR7/CR7/docker-compose.yml) — запуск брокера, бэкенда и фронтенда
  - [standart.beacons](CR7/CR7/standart.beacons) — координаты маяков (CSV `Name;X;Y`)
  - [standart.path](CR7/CR7/standart.path) — пример маршрута
  - [mosquitto/](CR7/CR7/mosquitto) — конфигурация брокера
  - [backend/](CR7/CR7/backend) — сервис вычисления координат и API
  - [frontend/](CR7/CR7/frontend) — Nuxt 3 UI
  - [esp32/](CR7/CR7/esp32) — прошивка для ESP32 (MicroPython)

Корневые файлы:
- [LICENSE](CR7/LICENSE) — лицензия Apache-2.0
- [README.md](CR7/README.md) — это руководство

## Ключевые папки и файлы

### Backend — [CR7/CR7/backend](CR7/CR7/backend)
- Конфиг: [config.py](CR7/CR7/backend/config.py)  
  Параметры MQTT и окна агрегирования: [`config.MQTT_SERVER`](CR7/CR7/backend/config.py), [`config.MQTT_PORT`](CR7/CR7/backend/config.py), [`config.MQTT_TOPIC`](CR7/CR7/backend/config.py), [`config.WINDOW_SEC`](CR7/CR7/backend/config.py), [`config.BEACONS_FILE`](CR7/CR7/backend/config.py).
- Маяки: [beacons.py](CR7/CR7/backend/beacons.py)  
  Глобальная мапа координат: [`beacons.BEACON_POSITIONS`](CR7/CR7/backend/beacons.py) (загружается из `standart.beacons`).
- MQTT: [mqtt_handler.py](CR7/CR7/backend/mqtt_handler.py)  
  Подписка, парсинг и сглаживание: [`mqtt_handler.init_mqtt`](CR7/CR7/backend/mqtt_handler.py), [`mqtt_handler.on_message`](CR7/CR7/backend/mqtt_handler.py), [`mqtt_handler.get_smoothed_rssi`](CR7/CR7/backend/mqtt_handler.py).
- Трилатерация: [trilateration.py](CR7/CR7/backend/trilateration.py)  
  Основной класс: [`RobustTrilateration`](CR7/CR7/backend/trilateration.py) (преобразование RSSI→дистанция, взвешивание, фильтрация, оценка точности).
- Состояние: [state.py](CR7/CR7/backend/state.py)  
  Хранение последней позиции: [`state.save_last_position`](CR7/CR7/backend/state.py), [`state.load_last_position`](CR7/CR7/backend/state.py).
- API: [api.py](CR7/CR7/backend/api.py)  
  Эндпоинты `/position`, `/beacons`; запуск сервера: [`api.run_api`](CR7/CR7/backend/api.py) (порт 3277).
- Точка входа: [main.py](CR7/CR7/backend/main.py)  
  Цикл сбора окна RSSI → трилатерация → сохранение → лог.

Сборка контейнера: [Dockerfile](CR7/CR7/backend/Dockerfile).

### Frontend — [CR7/CR7/frontend](CR7/CR7/frontend)
- Страница: [app/pages/index.vue](CR7/CR7/frontend/app/pages/index.vue) — запросы `/api/*`, запись пути и экспорт `sol.path`.
- Отрисовка: [app/components/map.vue](CR7/CR7/frontend/app/components/map.vue) — сетка, маяки, путь, позиция.
- Конфиг Nuxt/прокси: [nuxt.config.ts](CR7/CR7/frontend/nuxt.config.ts) — проксирование `/api` на бэкенд.
- Контейнер: [Dockerfile](CR7/CR7/frontend/Dockerfile).

### ESP32 — [CR7/CR7/esp32](CR7/CR7/esp32)
- Публикатор BLE→MQTT: [main.py](CR7/CR7/esp32/main.py)  
  Настройки Wi‑Fi/MQTT: `WIFI_SSID`, `WIFI_PASS`, `MQTT_SERVER`, `MQTT_PORT`, `MQTT_TOPIC`. Публикуется JSON `{"name":"beacon_X","rssi":-72}`.

### Mosquitto — [CR7/CR7/mosquitto](CR7/CR7/mosquitto)
- Конфиг брокера: [mosquitto.conf](CR7/CR7/mosquitto/mosquitto.conf).

### Файлы данных
- Формат маяков: [CR7/CR7/standart.beacons](CR7/CR7/standart.beacons)  
  CSV с `;`:
  ```
  Name;X;Y
  beacon_1;0;0
  beacon_2;10;0
  beacon_3;0;10
  ```
  Путь задаётся через [`config.BEACONS_FILE`](CR7/CR7/backend/config.py), используется в [`beacons.BEACON_POSITIONS`](CR7/CR7/backend/beacons.py).
- Пример маршрута: [CR7/CR7/standart.path](CR7/CR7/standart.path) (CSV `X;Y`), экспортируется фронтендом.

## API (кратко)

- GET `/api/position` — текущая позиция и метрики (см. [api.py](CR7/CR7/backend/api.py))
- GET `/api/beacons` — координаты маяков

## Полезные замечания

- Для Docker используйте `MQTT_SERVER="mosquitto"` в [`config.MQTT_SERVER`](CR7/CR7/backend/config.py). Для локального брокера — `"localhost"`.
- На ESP32 `MQTT_SERVER` должен быть IP/домен брокера, доступный из сети устройства (не `localhost`).
- Формат входящих сообщений описан в [`mqtt_handler.on_message`](CR7/CR7/backend/mqtt_handler.py). Значение `rssi` может быть числом или строкой, приводится к float.
- Окно усреднения управляется [`config.WINDOW_SEC`](CR7/CR7/backend/config.py).

## Лицензия

Apache-2.0, см. [LICENSE](CR7/LICENSE).