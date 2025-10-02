import os

# Путь к папке backend (этот файл)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Корень проекта — на уровень выше backend/
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# MQTT
MQTT_SERVER = "10.49.206.215"
MQTT_PORT = 1883
MQTT_TOPIC = "beacons/#"
WINDOW_SEC = 1.0  # окно сбора данных (сек)

# Полный путь к файлу маяков (в корне проекта)
BEACONS_FILE = os.path.join(PROJECT_ROOT, "standart.beacons")