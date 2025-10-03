CR7 — Инструкция по развертыванию на Linux

Эта инструкция подойдёт для Ubuntu/Debian. Для Fedora замените apt на dnf, для Arch — на pacman. Предполагается, что папка проекта уже есть на диске.

СОДЕРЖАНИЕ
1) Вариант A — запуск в Docker Compose (рекомендуется)
2) Вариант B — локальный запуск без Docker
3) Подключение ESP32 (опционально)
4) Проверка работы
5) Частые проблемы
6) Полезные команды

──────────────────────────────────────────────────────────────────────────────
1) Вариант A — Docker Compose (рекомендуется)

Требования:
- Docker Engine + Docker Compose Plugin

Установка Docker (Ubuntu):
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $UBUNTU_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

Запуск:
```bash
cd /path/to/your/repo
docker compose -f CR7/CR7/docker-compose.yml up -d --build
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

──────────────────────────────────────────────────────────────────────────────
2) Вариант B — локальный запуск без Docker

Требования:
- Mosquitto (брокер) и mosquitto-clients
- Python 3.10+ и venv
- Node.js LTS + pnpm (или npm)

Установка зависимостей (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients python3 python3-venv curl
# Node.js LTS через nvm:
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm install --lts
npm i -g pnpm
```

Запуск брокера:
```bash
# сервисно
sudo systemctl enable --now mosquitto
# проверить порт
ss -lnt | grep 1883
```

Бэкенд:
```bash
cd /path/to/your/repo/CR7/CR7/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# убедитесь, что в config.py:
# MQTT_SERVER = "localhost"
python main.py
```

Фронтенд:
```bash
cd /path/to/your/repo/CR7/CR7/frontend
pnpm i    # или npm i
pnpm dev  # откроется http://localhost:3000
```
Если фронтенд проксирует на контейнерный backend, укажите прокси на http://localhost:3277 в nuxt.config.ts.

──────────────────────────────────────────────────────────────────────────────
3) Подключение ESP32 (опционально)

- Прошейте MicroPython на ESP32.
- Отредактируйте CR7/CR7/esp32/main.py: WIFI_SSID, WIFI_PASS, MQTT_SERVER (IP вашего ПК), MQTT_PORT, MQTT_TOPIC.
- Загрузите файл:
```bash
pip install -U mpremote
mpremote connect auto fs cp CR7/CR7/esp32/main.py :main.py
```
ESP32 начнёт публиковать JSON в топик "beacons".

──────────────────────────────────────────────────────────────────────────────
4) Проверка работы

Без железа (эмуляция RSSI):
```bash
# подписка (терминал 1)
mosquitto_sub -h localhost -t 'beacons/#' -v

# публикация (терминал 2)
mosquitto_pub -h localhost -t beacons -m '{"name":"beacon_1","rssi":-70}'
```

Проверка API:
```bash
curl http://localhost:3277/position
curl http://localhost:3277/beacons
```

UI:
- Откройте http://localhost:3000
- Синие точки — маяки из CR7/CR7/standart.beacons (CSV Name;X;Y)
- Красная точка — текущая позиция; можно записать маршрут и сохранить sol.path

──────────────────────────────────────────────────────────────────────────────
5) Частые проблемы

- Docker: permission denied
  Решение: добавьте пользователя в группу docker (см. установку) и выполните newgrp docker.

- Пустой список маяков / нет позиции
  Проверьте CR7/CR7/standart.beacons и путь в config.BEACONS_FILE.
  Убедитесь, что в MQTT есть сообщения (mosquitto_sub показывает поток).

- Бэкенд не подключается к брокеру
  В Docker: MQTT_SERVER="mosquitto".
  Локально: MQTT_SERVER="localhost".
  Проверьте порт 1883 не занят и брокер запущен.

- Фронтенд не видит API
  Пропишите прокси на http://localhost:3277 в CR7/CR7/frontend/nuxt.config.ts.
  Проверьте, что backend слушает порт 3277 (логи).

- Конфликт портов (3000/3277/1883 заняты)
  Измените порт сервиса (Nuxt/Flask/Mosquitto) и соответствующие настройки в конфиге.

──────────────────────────────────────────────────────────────────────────────
6) Полезные команды

Docker Compose:
```bash
docker compose -f CR7/CR7/docker-compose.yml up -d --build
docker compose -f CR7/CR7/docker-compose.yml logs -f backend
docker compose -f CR7/CR7/docker-compose.yml down -v
```

Mosquitto:
```bash
sudo systemctl status mosquitto
mosquitto_sub -h localhost -t 'beacons/#' -v
mosquitto_pub -h localhost -t beacons -m '{"name":"beacon_1","rssi":-70}'
```

Backend (локально):
```bash
cd CR7/CR7/backend && . .venv/bin/activate && python main.py
```

Frontend (локально):
```bash
cd CR7/CR7/frontend && pnpm dev
```

Порты по умолчанию:
- Frontend: 3000
- Backend (API): 3277
- MQTT: 1883