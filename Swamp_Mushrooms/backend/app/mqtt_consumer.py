import json
import threading
import time
import paho.mqtt.client as mqtt
from .config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, TEAM
from .schema import ScanMessage
from .persistence import load_beacons, save_position
from .trilateration import trilateration

anchors = load_beacons()

def on_connect(client, userdata, flags, rc):
    print("MQTT connected", rc)
    # subscribe to wildcard topic for your team
    client.subscribe(f"hackyadro/{TEAM}/anchors/+/measurement")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        scan = ScanMessage(**data)
    except Exception as e:
        print("Invalid message:", e)
        return

    # run trilateration
    try:
        measured = [{"beacon_id": it.beacon_id, "rssi": it.rssi} for it in scan.scan]
        x,y = trilateration(anchors, measured)
        save_position(scan.device_id, x, y, scan.timestamp_us)
        print(f"Estimated {scan.device_id}: x={x:.2f} y={y:.2f}")
    except Exception as e:
        print("Position calc failed:", e)

def start_mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    return client
