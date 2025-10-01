# app/subscriber.py
import os, json
from datetime import datetime
import paho.mqtt.client as mqtt
from pathlib import Path

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.environ.get("MQTT_USER", "deviceuser")
MQTT_PASS = os.environ.get("MQTT_PASS", "secret")
TOPIC     = os.environ.get("MQTT_TOPIC", "beacons/#")
OUT_FILE  = Path(os.environ.get("OUT_FILE", "/data/beacons.log"))
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

def on_connect(client, userdata, flags, rc, properties=None):
    print("MQTT connected rc=", rc, "host=", MQTT_HOST)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    ts = datetime.utcnow().isoformat() + "Z"
    payload = msg.payload.decode("utf-8", errors="ignore")
    try:
        obj = {
            "received_at": ts,
            "topic": msg.topic,
            "payload": json.loads(payload)
        }
    except Exception:
        obj = {"received_at": ts, "topic": msg.topic, "payload_raw": payload}

    with OUT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    main()
