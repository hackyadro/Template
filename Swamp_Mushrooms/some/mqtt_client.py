import json, time
import paho.mqtt.client as mqtt
from rssi_filter import smooth_rssi, add_rssi_sample

def make_client(broker, port, input_topic, device_id, estimator, output_topic):
    def on_connect(cl, userdata, flags, rc):
        print(f"[INFO] Connected to MQTT {rc}")
        cl.subscribe(input_topic)
        print(f"[INFO] Subscribed to topic: {input_topic}")

    def on_message(cl, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            if data.get("device_id") != device_id:
                return
            now_us = data.get("timestamp_us", int(time.time() * 1e6))
            for s in data.get("scan", []):
                bid = s.get("beacon_id", "").strip().upper()
                rssi = s.get("rssi")
                if not rssi:
                    continue
                rssi_s = smooth_rssi(bid, rssi)
                estimator.update_rssi(bid, rssi_s, time.time())
                add_rssi_sample(bid, rssi)

        except Exception as e:
            print("[ERROR] on_message:", e)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker, port, 60)
    return client
