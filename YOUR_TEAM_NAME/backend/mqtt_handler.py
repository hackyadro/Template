import json
from collections import defaultdict
from statistics import median
import paho.mqtt.client as mqtt
from config import MQTT_SERVER, MQTT_PORT, MQTT_TOPIC

latest_rssi = defaultdict(lambda: None)
rssi_history = defaultdict(list)

ANCHOR_POINTS = {}  # сюда позже загрузим из beacons.py

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        name = payload.get("name")
        rssi = payload.get("rssi")
        if name and name in ANCHOR_POINTS:
            latest_rssi[name] = rssi
            rssi_history[name].append(rssi)
            if len(rssi_history[name]) > 5:
                rssi_history[name].pop(0)
    except Exception as e:
        print("Ошибка парсинга:", e)

def get_smoothed_rssi():
    return {name: median(history) for name, history in rssi_history.items() if history}

def init_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    return client