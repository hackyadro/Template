# Client for locator
install rust and bun

Не забыть везде заменить ip в 
HOST_ADDRESS = "10.145.244.78:8000"
и
SSID = "iPhone (Владимир)"
PASSWORD = "12345678"
run client: bun run tauri dev
или собрать билд в приложение: bun run tauri build

Использование
Задаёте карту
Запускаете устройство через 
python3 -m mpremote connect /dev/cu.url run itog_3.py
Перезагрузка и установка 0 позиции
Нажимаем на Старт и всё
потом стоп и скачать последнее