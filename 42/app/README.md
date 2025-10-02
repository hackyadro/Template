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
