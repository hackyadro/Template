# Real-Time Indoor Navigation
## Запуск
### Основная часть
```
docker-compose -f BezCode/docker-compose.yml up --build -d # убедитесь что запущен docker-desktop
```
### ESP устройство
```
cd BezCode/esp32 # для перехода в рабочую директорию устройства
# Измените параметры в файле config.json
scripts/flash    # скрипт для прошивки (достаточно прописать только при первом запуске)
scripts/run      # Загрузка кода на устройство и последующий запуск
# когда repl готов, используйте сочетание клавиш ctrl + d чтобы перезапустить устройство
```
Дополнительные скрипты (являются частью run)
```
scripts/upload   # загрузить обновлённый код на устройство
scripts/repl     # зайти в repl
```
### WEB-интерфейс
переходите на ```http://localhost:8501/```
на странице слева вы увидите поле для загрузки файла
<img width="2398" height="1347" alt="image" src="https://github.com/user-attachments/assets/6c7727e2-1ab4-4c0e-a2ec-dc3f507c0520" />
загрузите ваш .beacons файл
<img width="1073" height="115" alt="image" src="https://github.com/user-attachments/assets/aaa5b027-8bd8-4d31-88ca-0141eb2c9cbc" />
Нажмите Начать маршрут.
Если вы всё сделали правильно можете наблюдать за своим маршрутом.

