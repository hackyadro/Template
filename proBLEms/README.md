# Indoor Positioning System (proBLEms)

## Описание
Приложение состоит из трёх сервисов:
- **MQTT брокер** (Eclipse Mosquitto) – для обмена данными между устройствами.
- **Backend** (FastAPI, Python) – обрабатывает данные от маяков и клиентов.
- **Frontend** (Vite + Node.js) – веб-интерфейс для отображения данных.

Все сервисы запускаются через **Docker Compose**.

---

## Требования
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

## Запуск

1. Клонируйте репозиторий и перейдите в папку проекта:

```bash
git clone https://github.com/hackyadro-proBLEms/proBLEms.git
cd proBLEms
```

2. Запустите сервисы:
```bash
docker compose up --build
```

3. После успешного запуска будут доступны сервисы:
```bash
MQTT брокер: mqtt://localhost:1883

Backend API: http://localhost:8000
(доступна swagger-документация: http://localhost:8000/docs)

Frontend: http://localhost:8080
```

## Остановка
```bash
docker compose down
```
