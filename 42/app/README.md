## 1. Предварительно
- Установите **Docker** и **Docker Compose**.  
  - Linux:  
    ```bash
    sudo apt update
    sudo apt install docker.io docker-compose -y
    sudo systemctl enable --now docker
    ```

## 2. Клонирование репозитория
```bash
git clone git@github.com:your/repo.git
cd repo
```

## 3. Запуск
Докер файл лежит в подпапке репозитория 42, так что перед выполнением
перейдите ```cd 42/```

```bash
docker compose up --build
```

## 4. Проверка работы
- MQTT брокер: `localhost:1883`
- Подписчик пишет логи в `telemetry_log.csv`
- Streamlit доступен по адресу: [http://localhost:8501](http://localhost:8501)

## 5. Остановка
```bash
docker compose down
```

## 6. Полезные команды
- Просмотр логов:
  ```bash
  docker compose logs -f
  ```
- Пересобрать контейнеры с новым кодом:
  ```bash
  docker compose up -d --build
  ```
- Запуск контейнеров на фоне:
  ```
  docker compose up -d
  ```
- Перезапустить сервисы (без пересборки):
  ```
  docker compose restart
  ```
- Остановить контейнеры:
  ```
  docker compose down
  ```
- Посмотреть список контейнеров:
  ```
  docker ps
  ```
- Посмотреть статус сервисов в compose:
  ```
  docker compose ps
  ```


## 7. Настройка аутентификации MQTT (Mosquitto)

По умолчанию Mosquitto может работать без пароля, но для безопасности рекомендуется использовать файл `passwd`.

В нашем проекте файл `passwd` хранится **в корне проекта** (рядом с `docker-compose.yml`).

### 8.1 Создание файла и добавление пользователя
В нашем проекте используется фиксированный пользователь **42** с паролем **123123**.

Выполните команду для создания файла и пользователя:

```
touch passwd
```

```
docker run --rm -it -v $(pwd)/passwd:/mosquitto/config/passwd eclipse-mosquitto sh -c "echo '42:$(mosquitto_passwd -b /dev/stdout 42 123123 | tail -n1 | cut -d: -f2)' > /mosquitto/config/passwd"
```

### 8.2 Установка прав доступа
Mosquitto требует, чтобы файл был приватным. Настроим права:

```bash
chmod 0600 passwd
```

Теперь доступ только у владельца.

### 8.3 Конфигурация Docker Compose
В `docker-compose.yml` должен быть примонтирован файл `passwd`:

```yaml
services:
  mqtt_broker:
    image: eclipse-mosquitto:2
    volumes:
      - ./docker/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./passwd:/mosquitto/config/passwd
    ports:
      - "1883:1883"
      - "9001:9001"
```

А в `docker/mosquitto.conf` должна быть строка:

```
password_file /mosquitto/config/passwd
```

### 8.4 Перезапуск контейнера
После настройки перезапустите брокер:

```bash
docker compose up -d --build
```

### 8.5 Подключение клиентов
Теперь при подключении используйте логин и пароль:

#### Python (paho-mqtt)
```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.username_pw_set("username", "password")
client.connect("localhost", 1883, 60)
client.loop_start()
```

---

Теперь MQTT-брокер требует авторизацию.  

## 9. Запуск всей системы

```bash
docker compose up -d --build
```

После запуска доступны:
- MQTT брокер на порту **1883**
- Streamlit UI: [http://localhost:8501](http://localhost:8501)

## 10. Проверка подключения

После запуска системы можно убедиться, что данные с ESP поступают в брокер и обрабатываются подписчиком.

Для этого откройте логи сервиса `subscriber`:

```bash
docker compose logs -f subscriber
```

Вы должны увидеть сообщения вида

subscriber  | Connected: 0
subscriber  | Logging to: /app/telemetry_log.csv
subscriber  | 2025-10-03T10:21:00 esp32-34cd0b33a6c4 {"seq": 15, "rssi": -62, "uptime_s": 123, ...}

Если такие строки появляются — значит, MQTT брокер и подписчик работают корректно, и данные от ESP успешно принимаются.

