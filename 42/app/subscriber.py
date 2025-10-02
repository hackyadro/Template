# subscriber.py
import json
import csv
from datetime import datetime
from pathlib import Path
import paho.mqtt.client as mqtt

BROKER_HOST = "10.175.95.190"
BROKER_PORT = 1883
TOPIC = "devices/esp32/telemetry"

CSV_PATH = Path("telemetry_log.csv")
FIELDS = ["ts", "device_id", "seq", "ip", "uptime_s", "rssi", "beacons_json"]

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Connected:", reason_code)
    client.subscribe(TOPIC)
    print("Logging to:", CSV_PATH.resolve())

def on_message(client, userdata, msg):
    ts = datetime.now().isoformat(timespec="seconds")
    payload = msg.payload.decode("utf-8", errors="replace")
    print(f"[{ts}] {msg.topic} -> {payload}")

    # Парсим JSON безопасно
    try:
        d = json.loads(payload)
    except Exception:
        # если прилетело не-JSON — просто положим как сырой текст
        d = {"device_id": None, "seq": None, "ip": None, "uptime_s": None, "rssi": None, "beacons": payload}

    row = {
        "ts": ts,
        "device_id": d.get("device_id"),
        "seq": d.get("seq"),
        "ip": d.get("ip"),
        "uptime_s": d.get("uptime_s"),
        "rssi": d.get("rssi"),
        # список маяков сериализуем обратно в JSON, чтобы в CSV не «расползался» из-за запятых
        "beacons_json": json.dumps(d.get("beacons", []), ensure_ascii=False)
    }

    newfile = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if newfile:
            w.writeheader()
        w.writerow(row)

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pc-subscriber")
    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set("devices/esp32/status", payload="pc_offline", qos=1, retain=False)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nBye")
        client.disconnect()

if __name__ == "__main__":
    main()
