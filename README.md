# Хакатон YADRO. Команда "Богатыри"

## Структура решения
<img width="1078" height="571" alt="hackathon project structure" src="https://github.com/user-attachments/assets/d9d899a2-a40f-48c5-9a14-ddbc87f8f82d" />


## Инструкция по развёртыванию системы
1. Подготовка среды
Убедитесь, что у вас установлены:
- usbipd (`winget install --id=dorssel.usbipd-win -e`) и добавьте usbipd в PATH, для этого напишите эту команду в PowerShell `export PATH=$PATH:"/c/ProgramFiles/usbipd-win`
- uvicorn. `pip install uvicorn`
- fastapi. `pip install fastapi`

3. Сервис контроллера (Hardware + Firmware)
Подключите контроллер (показанный на схеме ESP32 или аналог).\
Загрузите на него прошивку, по данной инструкции: https://micropython.org/download/ESP32_GENERIC_S3/ \
В командной строке с правами администратора выполните команду `usbipd list` \
Найдите в списке подключенный контроллер и напишите `usbipd  ` \


5. Запуск Frontend & Backend

## Инструкция по использованию системы
1) Загрузить файл .beacons с расположением маячков
2) Задать частоту обновления маршрута
3) Нажать кнопку "Начать маршрут"
