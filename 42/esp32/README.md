# Загрузка кода на плату ESP32

## Прошивка платы
Для того, чтобы плата работала с файлами на MicroPython, её следует прошить. 

Инструкцию можно найти [здесь](https://micropython.org/download/ESP32_GENERIC/).

## Загрузка файла в плату
Рекомендуем использовать простую и удобную в интерфейсе Thonny IDE.

1. Установите IDE с [официального сайта](https://thonny.org/)
2. Зайдите в Tools → Options → Interpreter
    - В верхнем меню выберите MicroPython (ESP32)
    - В нижнем выберите порт с подключённой платой
3. Откройте в IDE файл boot.py из этой папки
> [!WARNING]
> Не забудьте поменять константы в начале файла boot.py (строчки 14-20)
4. Нажмите Ctrl-S или в View включите отображение Files и перенесите boot.py в появившееся нижнее окно

Теперь на плате ESP32 можно нажать кнопку RST и программа начнёт своё исполнение.

## Развёртывание серверной части (Docker)

Серверная часть включает:
- **MQTT брокер** (Mosquitto)
- **подписчик** на телеметрию (Python)
- **Streamlit UI** для визуализации (`http://localhost:8501`)

# Развёртывание серверной части (Docker)

Серверная часть включает:
- **MQTT брокер** (Mosquitto)
- **подписчик** на телеметрию (Python)
- **Streamlit UI** для визуализации (`http://localhost:8501`)

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
- Пересобрать контейнеры:
  ```bash
  docker compose up --build
  ```
