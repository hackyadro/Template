# Хакатон Yadro

Здесь представлено решение поставленной в рамках хакатона от лаборатории "Yadro" задачи

---

## Требования

- [Go](https://golang.org/) >= 1.20
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- TODO: дополнить

---

## Сборка и запуск через Docker Compose

1. Склонируйте репозиторий:

```bash
git clone https://github.com/UnemployedTocha/Tri_sira.git
```

2. Заполните конфиг файл(Tri_sira_team/Tri_sira_team/.env). Пример который можно использовать:
TODO: реализовать тестовый конфиг файл
```
SERVICE_PORT=8089
SERVICE_INTERNAL_PORT=8098

MOSQUITTO_USER=user
MOSQUITTO_PASSWORD=qwerty
MOSQUITTO_TOPIC=some_topic
MOSQUITTO_PORT=1833
MOSQUITTO_INTERNAL_PORT=1833 # Если менять, то менять надо и значение у listener в mosquitto.conf :(
```

3. Соберите и запустите контейнеры:
```bash
cd Tri_sira_team/backend
docker-compose up --build
```
