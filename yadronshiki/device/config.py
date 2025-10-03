import os

def load_env(path="../.env"):
    config = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    except Exception as e:
        print("Failed to read .env:", e)
    return config


# Загружаем при импорте
env = load_env()

# Настройки
MQTT_BROKER   = env.get("MQTT_BROKER", "localhost")
MQTT_PORT     = int(env.get("MQTT_PORT", 1883))

WIFI_SSID     = env.get("WIFI_SSID", "")
WIFI_PASS = env.get("WIFI_PASSWORD", "")

MQTT_CLIENT_ID = b"esp32-s3-ble"
MQTT_TOPIC = b"beacons/discovered"

SCAN_DURATION_MS = 333
