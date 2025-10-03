## 1. Предварительно
- Установите **Docker** и **Docker Compose**.  
  - Linux:  
    ```bash
    sudo apt update
    sudo apt install docker docker-compose -y
    sudo systemctl enable --now docker
    ```

## 2. Клонирование репозитория
```bash
git clone git@github.com:your/repo.git
cd repo
```

## 3. Запуск
Докер файл лежит в подпапке репозитория 42, так что перед выполнением
перейдите 
```bash
cd 42/
```

прежде чем начать работу с докером, необходимо открыть порты

```bash
sudo ufw start
sudo ufw allow 1883/tcp
sudo ufw/allow 8501/tcp
```

В случае если используется порт

```bash
sudo systemctl stop mosquitto
```

подключиться в свою сеть и узнать ip
```bash
hostname -I
```

Далее в скрипте запуска устройства esp32 поменять поля под сеть в которой находится хост и вписать в одно из полей хост ip

```bash
docker compose up --build
```

Следующим шагом запускаете контейнеры на фоне

```bash
docker compose up -d
```

Скорее всего вы увидите ошибки Permission denied. Читайте пункт 7 о том как создать и установить полльзователя для корректно работы докер контейнра

Далее вам необходимо запустить устройство с его boot файлом (читать в README.md из папки esp32.)


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
rmdir docker/passwd/
touch docker/passwd
```

```
sudo docker run --rm \
  -v "$(pwd)/docker:/mosquitto/config:Z" \
  eclipse-mosquitto \
  mosquitto_passwd -b -c /mosquitto/config/passwd 42 123123
```


### 8.2 Установка прав доступа
Mosquitto требует, чтобы файл был приватным. Настроим права:

```bash
sudo chmod 600 docker/passwd
```

```bash
sudo chmod 755 app/*
```

```bash
sudo chmod 644 app/subscriber
```

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

В случае если не получилось запустить через docker 

В папке 42/app
```
python3 -m venv .venv
```
```
source .venv/bin/activate
```
```
pip install -r requirements.txt
```

Все шаги с ufw и запуском бута. 

```
python3 app/app.py
```

в другом терминале

```
python3 app/subscriber.py
```
