# Indoor Navigation Backend

Python приложение для indoor-навигации на основе BLE/Beacon маяков с использованием RSSI для определения позиции.

## Возможности

- 📍 **Позиционирование по RSSI** - определение координат на основе силы сигнала от BLE маяков
- 🗺️ **Трилатерация** - точный расчет позиции при наличии 3+ маяков
- 📊 **Хранение траекторий** - восстановление пути передвижения
- 🔌 **REST API** - полноценное API для работы с маяками, измерениями и позициями
- 🐳 **Docker** - легкое развертывание с PostgreSQL

## Технологии

- **FastAPI** - современный веб-фреймворк
- **PostgreSQL** - хранение данных
- **SQLAlchemy** - ORM для работы с БД
- **NumPy** - математические вычисления для позиционирования
- **Docker & Docker Compose** - контейнеризация

## Быстрый старт

### Запуск с Docker

```bash
cd backend
docker-compose up --build
```

API будет доступен по адресу: `http://localhost:8000`

PostgreSQL будет доступна по порту: `5432`

### Проверка работоспособности

```bash
curl http://localhost:8000/health
```

## API Endpoints

### Документация API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Основные endpoints

#### Маяки (Beacons)

- `GET /beacons` - получить список всех маяков
- `GET /beacons/{id}` - получить информацию о маяке
- `POST /beacons` - создать новый маяк
- `DELETE /beacons/{id}` - удалить маяк

**Пример создания маяка:**
```bash
curl -X POST http://localhost:8000/beacons \
  -H "Content-Type: application/json" \
  -d '{
    "name": "beacon_1",
    "x_coordinate": 3.0,
    "y_coordinate": -2.4,
    "description": "Маяк в коридоре"
  }'
```

#### RSSI Измерения

- `GET /measurements` - получить список измерений
- `GET /measurements?beacon_id={id}` - измерения для конкретного маяка
- `POST /measurements` - создать новое измерение

**Пример создания измерения:**
```bash
curl -X POST http://localhost:8000/measurements \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": 1,
    "rssi_value": -65
  }'
```

#### Позиционирование

- `POST /positions/calculate` - вычислить текущую позицию
- `GET /positions` - получить историю позиций

**Пример вычисления позиции:**
```bash
curl -X POST http://localhost:8000/positions/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "measurements": [
      {"beacon_id": 1, "rssi_value": -65},
      {"beacon_id": 2, "rssi_value": -72},
      {"beacon_id": 3, "rssi_value": -58}
    ],
    "save_trajectory": true
  }'
```

#### Траектории

- `GET /trajectories` - список всех сессий
- `GET /trajectories/{session_id}` - получить траекторию для сессии

## Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI приложение и endpoints
│   ├── models.py         # Pydantic модели
│   ├── database.py       # Подключение к БД
│   └── positioning.py    # Алгоритмы позиционирования
├── migrations/
│   └── 001_initial_schema.sql
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Алгоритмы позиционирования

### 1. RSSI → Distance

Преобразование силы сигнала в расстояние:
```
distance = 10 ^ ((RSSI_AT_1M - RSSI) / (10 * PATH_LOSS_EXPONENT))
```

### 2. Трилатерация

Используется метод наименьших квадратов для решения системы уравнений при наличии 3+ маяков.

### 3. Взвешенный центроид

Запасной метод при недостатке маяков - вычисляет позицию как взвешенный центр масс.

## База данных

### Схема

- **beacons** - информация о BLE маяках
- **rssi_measurements** - измерения силы сигнала
- **positions** - вычисленные позиции
- **trajectories** - траектории движения

### Подключение к PostgreSQL

```bash
docker exec -it indoor_navigation_db psql -U indoor_user -d indoor_navigation
```

## Переменные окружения

- `DATABASE_URL` - URL подключения к PostgreSQL (по умолчанию: `postgresql+asyncpg://indoor_user:indoor_pass@postgres:5432/indoor_navigation`)

## Разработка

### Установка зависимостей локально

```bash
pip install -r requirements.txt
```

### Запуск без Docker

```bash
# Запустить PostgreSQL отдельно
# Выполнить миграции
psql -U indoor_user -d indoor_navigation -f migrations/001_initial_schema.sql

# Запустить приложение
uvicorn app.main:app --reload
```

## Примеры использования

### Инициализация маяков из файла

Если у вас есть файл `standart.beacons` с координатами маяков:

```bash
# Пример скрипта для загрузки маяков
while IFS=';' read -r name x y; do
  if [ "$name" != "Name" ]; then
    curl -X POST http://localhost:8000/beacons \
      -H "Content-Type: application/json" \
      -d "{\"name\": \"$name\", \"x_coordinate\": $x, \"y_coordinate\": $y}"
  fi
done < standart.beacons
```

## License

MIT
