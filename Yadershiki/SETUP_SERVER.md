## Подготовка окружения

Перед запуском убедитесь, что установлены:
- **Docker**
- **Docker Compose**
- ESP32 устройства с прошитым кодом для сканирования BLE-маяков


Сборка окружения

Запуск сервисов:

docker-compose up

Проверка работы контейнеров:

docker-compose ps


Управление сервисами

# Просмотр логов приложения
docker-compose logs app -f

# Просмотр логов MQTT брокера
docker-compose logs emqx -f

# Общие логи всех сервисов
docker-compose logs -f

# Остановка всех сервисов
docker-compose down

# Полная пересборка и запуск
docker-compose down
docker-compose build --no-cache
docker-compose up -d


Тестирование MQTT

# Установка MQTT клиента
npm install -g mqtt

# Подписка на топик для мониторинга данных
mqtt sub -t 'beacons/#' -h localhost -p 1883 -v


Проверка состояния API
# Проверка здоровья приложения
curl http://localhost:8080/health

# Получение статуса буферов
curl http://localhost:8080/status