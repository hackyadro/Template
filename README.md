# Real-Time Indoor Navigation
## Запуск
### Основная часть
```
docker-compose -f BezCode/docker-compose.yml up --build -d # убедитесь что запущен docker-desktop
```
### ESP устройство
```
cd BezCode/esp32 # для перехода в рабочую директорию устройства
scripts/flash    # скрипт для прошивки (достаточно прописать только при первом запуске)
scripts/run      # Загрузка кода на устройство и последующий запуск
# когда что repl готов, используйте сочетание клавиш ctrl + d чтобы перезапустить устройство
```
Дополнительные скрипты (являются частью run)
```
scripts/upload   # загрузить обновлённый код на устройство
scripts/repl     # зайти в repl
```
### WEB-интерфейс
переходите на ```http://localhost:8501/```
на странице слева вы увидите поле для загрузки файла
<img width="2480" height="1380" alt="image" src="https://github.com/user-attachments/assets/82058417-085a-46e7-83d0-3ab8b006f6f3" />
загрузите ваш .beacons файл
<img width="1073" height="115" alt="image" src="https://github.com/user-attachments/assets/aaa5b027-8bd8-4d31-88ca-0141eb2c9cbc" />
Нажмите Начать маршрут.
Если вы всё сделали правильно можете наблюдать за своим маршрутом.
