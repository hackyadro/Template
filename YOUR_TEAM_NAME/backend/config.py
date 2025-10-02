import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # путь к /backend
PROJECT_ROOT = os.path.dirname(BASE_DIR)              # путь к корню проекта

MQTT_SERVER = "10.49.206.215"
MQTT_PORT   = 1883
MQTT_TOPIC  = "beacons/#"
WINDOW_SEC  = 1.0  # окно сбора данных

# Файл маяков в корне
BEACONS_FILE = os.path.join(PROJECT_ROOT, "standart.beacons")