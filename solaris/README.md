# hackyadro/Solaris

Проект на хакатон лаборатории YADRO "ТЕХНОЛОГИЯ НАВИГАЦИИ ВНУТРИ ПОМЕЩЕНИЙ"


Этот проект включает:

* ESP32 с прошивкой MicroPython
* MQTT-брокер (Mosquitto)
* Desctop приложение ss

## Как установить и запустить приложение?
## 1. Подготовка ESP32
### Установка MicroPython

1. Установите прошивку MicroPython на ESP32 (см. официальную [инструкцию](https://micropython.org/download/esp32/)).

### Загрузка кода на плату

#### 1. Клонирование репозитория

```bash
git clone https://github.com/Pyrokines17/Solaris.git
cd ...
```

#### 2. Настройка конфигурации

В `boot.py` замените данные WiFi:

```python
WIFI_SSID = 'ВАШ_WIFI_SSID'
WIFI_PASSWORD = 'ВАШ_WIFI_ПАРОЛЬ'
```

В `main.py` настройте MQTT:

```python
MQTT_BROKER = "192.168.1.100"  # IP вашего MQTT брокера
MQTT_PORT = 1883
MQTT_TOPIC = "hakaton/board"
CLIENT_ID = "esp32_board"
```

#### 3. Загрузка файлов на ESP32

**Способ 1. Ampy**

```bash
pip install adafruit-ampy
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 ls
ampy --port /dev/ttyUSB0 reset
```

> При ошибке прав используйте `sudo`.

**Способ 2. Thonny IDE**

* Установите Thonny:

  * Ubuntu/Debian:

```bash
    sudo apt update
    sudo apt install python3-tk thonny
```
  * Windows: скачайте с [официального сайта](https://thonny.org/).
* Настройте интерпретатор:

* Добавьте своего пользователя в группу для доступа к порту платы
```bash
    sudo usermod -aG dialout aleksandra
```


  * **Tools → Options → Interpreter**
  * Interpreter: *MicroPython (ESP32)*
  * Port: `/dev/ttyUSB0` или `COM3` или `ACM0`
* Загрузите `boot.py` и `main.py` на устройство (**File → Save as → MicroPython device**).
* Перезапустите ESP32 (**Ctrl+F2**).

> При ошибке
#### 4. Запуск

Подключите ESP32 к аккумулятору или USB. 🎉

---

## 2. Установка MQTT-брокера (Mosquitto)

### Установка (Linux)

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
```

### Запуск и автозапуск

```bash
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

Брокер автоматически работает на порту **1883**.

---

## 3. Запуск настольного приложения

### Подготовка окружения

1. Установите [Qt](https://www.qt.io/download-qt-installer)
2. Установите библиотеку **MQTT** (см. инструкцию в `lib/connector/`).
3. Установите зависимости из папки `gen`.
4. Клонируйте репозиторий.

### Проверка окружения

* Убедитесь, что ESP32 подключено и работает.
* MQTT-брокер Mosquitto запущен.

### Сборка и запуск

```bash
cmake -B build
cd build
ninja
```

