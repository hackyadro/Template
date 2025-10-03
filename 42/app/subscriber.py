import json
import csv
import socket
from datetime import datetime
from pathlib import Path
import paho.mqtt.client as mqtt
import os

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

BROKER_HOST = os.environ.get("BROKER_HOST") or get_local_ip()
BROKER_PORT = int(os.environ.get("BROKER_PORT", "1883"))
TOPIC = "devices/esp32/telemetry"
MQTT_USER   = os.environ.get("MQTT_USER")
MQTT_PASS   = os.environ.get("MQTT_PASS")

CSV_PATH = Path("telemetry_log.csv")
FIELDS = ["ts", "device_id", "seq", "ip", "uptime_s", "rssi", "beacons_json"]

with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Connected:", reason_code)
    client.subscribe(TOPIC)
    print("Logging to:", CSV_PATH.resolve())

def on_message(client, userdata, msg):
    ts = datetime.now().isoformat(timespec="seconds")
    payload = msg.payload.decode("utf-8", errors="replace")
    print(f"[{ts}] {msg.topic} -> {payload}")

    try:
        d = json.loads(payload)
    except Exception:
        d = {"device_id": None, "seq": None, "ip": None, "uptime_s": None, "rssi": None, "beacons": payload}

    row = {
        "ts": ts,
        "device_id": d.get("device_id"),
        "seq": d.get("seq"),
        "ip": d.get("ip"),
        "uptime_s": d.get("uptime_s"),
        "rssi": d.get("rssi"),
        "beacons_json": json.dumps(d.get("beacons", []), ensure_ascii=False)
    }

    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writerow(row)

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pc-subscriber")
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    print(f"MQTT auth user={MQTT_USER!r}, host={BROKER_HOST}:{BROKER_PORT}")
    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set("devices/esp32/status", payload="pc_offline", qos=1, retain=False)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()

if __name__ == "__main__":
    main()
