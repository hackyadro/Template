import json, time
from config import BEACONS, LAST_VALUES, buf_lock
from rssi_utils import smooth_rssi

CONTROL = {
    "freq": 2.0,
    "recording": False,
    "path": []
}

def on_connect(cl, userdata, flags, rc):
    print(f"[INFO] Connected to MQTT {rc}")
    cl.subscribe(userdata["input_topic"])
    print(f"[INFO] Subscribed to topic: {userdata['input_topic']}")

def on_message(cl, userdata, msg):
    """Обработка входящих сообщений с RSSI"""
    try:
        data = json.loads(msg.payload.decode())
        if data.get("device_id") != userdata["device_id"]:
            return
        now_us = data.get("timestamp_us", int(time.time() * 1e6))

        with buf_lock:
            for s in data.get("scan", []):
                bid = s.get("beacon_id", "").strip().upper()
                if bid not in BEACONS:
                    continue
                rssi = s.get("rssi")
                if rssi is None:
                    continue
                rssi_s = smooth_rssi(bid, rssi)
                LAST_VALUES[bid] = (rssi_s, time.time())
    except Exception as e:
        print("[ERROR] on_message:", e)
