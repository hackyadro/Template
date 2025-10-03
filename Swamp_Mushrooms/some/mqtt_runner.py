import json, time, threading, argparse, math
from collections import defaultdict, deque
import paho.mqtt.client as mqtt
import pos_estimator

# словарь координат маяков
BEACONS = {
    "UCUVUVUVUVUVUVUVVUVUV": (-1.0, -0.7),
    "KKKKKKKKKKKKKKKKKKKKK": (0.7, 4.0),
    "ZZZZZZZZZZZZZZZZZZZZZ": (0.7, -0.7),
}

# глобальное хранилище последних значений
LAST_VALUES = {}
RSSI_FILT = {}  # для экспоненциального сглаживания
ALPHA = 0.15    # коэффициент сглаживания (0.1–0.2)


# параметры маяков
BEACON_PARAMS = {k: {"tx_power": -70.0, "n": 3.3} for k in BEACONS.keys()}

WINDOW_SECONDS = 5.0
buf_lock = threading.Lock()

# EKF instance
ekf = pos_estimator.create_ekf()

def rssi_to_distance(rssi, tx_power, n):
    return 10 ** ((tx_power - rssi) / (10.0 * n))

def smooth_rssi(bid, rssi):
    """Экспоненциальное сглаживание RSSI"""
    if bid not in RSSI_FILT:
        RSSI_FILT[bid] = rssi
    else:
        RSSI_FILT[bid] = ALPHA * rssi + (1 - ALPHA) * RSSI_FILT[bid]
    return RSSI_FILT[bid]

def on_connect(cl, userdata, flags, rc):
    print(f"[INFO] Connected to MQTT {rc}")
    cl.subscribe(userdata["input_topic"])
    print(f"[INFO] Subscribed to topic: {userdata['input_topic']}")

def on_message(cl, userdata, msg):
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

def compute_stats_for_window(window_s=WINDOW_SECONDS):
    beacons_list, dists, variances, timestamps = [], [], [], []
    cutoff = time.time() - window_s
    for bid, coords in BEACONS.items():
        if bid not in LAST_VALUES:
            continue
        rssi, t = LAST_VALUES[bid]
        if t < cutoff:
            continue
        tx = BEACON_PARAMS[bid]["tx_power"]
        n = BEACON_PARAMS[bid]["n"]
        dist = rssi_to_distance(rssi, tx, n)

        b = pos_estimator.Beacon()
        b.x, b.y = coords
        beacons_list.append(b)

        dists.append(dist)
        # адаптивная дисперсия: чем выше амплитуда шумов RSSI, тем больше вес ошибки
        var = max(1.0, abs(rssi) * 0.05)  
        variances.append(var)
        timestamps.append(t)
    return beacons_list, dists, variances, timestamps

def estimator_loop(client, device_id, output_topic, freq_hz):
    period = 1.0 / freq_hz
    last = (0.0, 0.0)
    while True:
        start = time.time()
        beacons_list, dists, variances, timestamps = compute_stats_for_window()
        if len(beacons_list) >= 3:
            if last == (0.0, 0.0):
                xs = [b.x for b in beacons_list]
                ys = [b.y for b in beacons_list]
                init_x = sum(xs) / len(xs)
                init_y = sum(ys) / len(ys)
            else:
                init_x, init_y = last
            try:
                res = pos_estimator.estimate_position(
                    beacons_list, dists, variances, init_x, init_y, True, 1.0 / freq_hz
                )
                # EKF предсказание
                ekf.predict(1.0 / freq_hz)

                # проверка на скачок
                pred_x, pred_y, _, _ = ekf.get_state()
                meas_x, meas_y = res.x, res.y
                var_xx = res.cov_xx + 1e-3
                var_yy = res.cov_yy + 1e-3
                var_xy = res.cov_xy

                ekf.update(meas_x, meas_y, var_xx, var_xy, var_yy)
                x, y, vx, vy = ekf.get_state()
                last = (x, y)
                out = {
                    "device_id": device_id,
                    "timestamp": int(time.time() * 1e6),
                    "x": float(x),
                    "y": float(y),
                    "v": {"vx": float(vx), "vy": float(vy)},
                    "cov": {"xx": res.cov_xx, "xy": res.cov_xy, "yy": res.cov_yy},
                }
                client.publish(output_topic, json.dumps(out))
            except Exception as e:
                print("[ERROR] estimation:", e)
        else:
            print("[WARN] Мало маяков для расчёта")
        elapsed = time.time() - start
        to_sleep = period - elapsed
        if to_sleep > 0:
            time.sleep(to_sleep)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--freq", type=float, default=2.0)
    parser.add_argument("--input-topic", default="esp32/ble")
    parser.add_argument("--output-topic", default="ble/position")
    parser.add_argument("--device-id", default="tracker_1")
    args = parser.parse_args()

    client = mqtt.Client(userdata={"input_topic": args.input_topic, "device_id": args.device_id})
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, 60)

    t = threading.Thread(
        target=estimator_loop,
        args=(client, args.device_id, args.output_topic, args.freq),
        daemon=True,
    )
    t.start()
    client.loop_forever()

if __name__ == "__main__":
    main()
