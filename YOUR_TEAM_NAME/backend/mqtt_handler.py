# mqtt_handler.py
import json
from collections import defaultdict
from statistics import median
import paho.mqtt.client as mqtt
import threading
import time

from config import MQTT_SERVER, MQTT_PORT, MQTT_TOPIC
from beacons import BEACON_POSITIONS

# Хранилище последних RSSI и история по каждому маяку
latest_rssi = defaultdict(lambda: None)
rssi_history = defaultdict(list)

# MQTT client (инициализируется функцией init_mqtt)
_client = None
_client_lock = threading.Lock()

def on_message(client, userdata, msg):
    """Разбор входящих MQTT-сообщений."""
    try:
        payload_text = msg.payload.decode('utf-8', errors='ignore')
        # ожидаем JSON: {"name": "beacon_1", "rssi": -72}
        payload = json.loads(payload_text)
        name = payload.get("name")
        rssi = payload.get("rssi")

        # иногда rssi приходит как строка — попробуем привести
        if isinstance(rssi, str):
            try:
                rssi = float(rssi)
            except Exception:
                # игнорируем некорректное значение
                rssi = None

        if name and (name in BEACON_POSITIONS) and (rssi is not None):
            latest_rssi[name] = rssi
            # сохраняем историю (скользящее окно)
            rssi_history[name].append(rssi)
            if len(rssi_history[name]) > 10:
                rssi_history[name].pop(0)
    except json.JSONDecodeError:
        # если пришёл не JSON, попробуем парсить простым форматом "name:rssi"
        try:
            payload_text = payload_text.strip()
            if ":" in payload_text:
                name, rssi_str = payload_text.split(":", 1)
                name = name.strip()
                rssi = float(rssi_str.strip())
                if name in BEACON_POSITIONS:
                    latest_rssi[name] = rssi
                    rssi_history[name].append(rssi)
                    if len(rssi_history[name]) > 10:
                        rssi_history[name].pop(0)
        except Exception:
            # молча игнорируем неподдерживаемые форматы
            pass
    except Exception as e:
        print("Ошибка парсинга MQTT-пейлоада:", e)

def get_smoothed_rssi():
    """Возвращает сглаженные значения RSSI используя медиану (по истории)."""
    smoothed = {}
    for name, history in rssi_history.items():
        if history:
            smoothed[name] = median(history)
    return smoothed

def init_mqtt():
    """Инициализация и запуск MQTT клиента. Возвращает объект клиента."""
    global _client
    with _client_lock:
        if _client is not None:
            return _client

        client = mqtt.Client()
        client.on_message = on_message

        try:
            client.connect(MQTT_SERVER, MQTT_PORT, 60)
            client.subscribe(MQTT_TOPIC)
            client.loop_start()
            _client = client
            print(f"MQTT: подключение к {MQTT_SERVER}:{MQTT_PORT}, подписка на {MQTT_TOPIC}")
            return client
        except Exception as e:
            print("MQTT: не удалось подключиться:", e)
            return None

def stop_mqtt():
    global _client
    with _client_lock:
        if _client is not None:
            try:
                _client.loop_stop()
                _client.disconnect()
            except Exception:
                pass
            _client = None