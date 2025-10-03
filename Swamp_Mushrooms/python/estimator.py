import time, json
import pos_estimator
from config import BEACONS, BEACON_PARAMS, LAST_VALUES, WINDOW_SECONDS, ekf
from rssi_utils import rssi_to_distance
import asyncio

def compute_stats_for_window(window_s=WINDOW_SECONDS):
    """Формируем список маяков и расстояний для текущего окна"""
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

        var = max(1.0, abs(rssi) * 0.05)
        variances.append(var)
        timestamps.append(t)

    return beacons_list, dists, variances, timestamps


def estimator_loop(client, device_id, output_topic, freq_hz, ws_broadcast=None):
    period = 1.0 / freq_hz
    last = (0.0, 0.0)

    while True:
        from mqtt_handler import CONTROL
        period = 1.0 / CONTROL["freq"]

        start = time.time()
        beacons_list, dists, variances, timestamps = compute_stats_for_window()

        if len(beacons_list) >= 3:
            if last == (0.0, 0.0):
                xs = [b.x for b in beacons_list]
                ys = [b.y for b in beacons_list]
                init_x, init_y = sum(xs) / len(xs), sum(ys) / len(ys)
            else:
                init_x, init_y = last

            try:
                res = pos_estimator.estimate_position(
                    beacons_list, dists, variances, init_x, init_y, True, 1.0 / freq_hz
                )

                ekf.predict(1.0 / freq_hz)
                pred_x, pred_y, _, _ = ekf.get_state()
                meas_x, meas_y = res.x, res.y
                var_xx, var_yy, var_xy = res.cov_xx + 1e-3, res.cov_yy + 1e-3, res.cov_xy

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

                # отправка координат в WS
                if ws_broadcast:
                    asyncio.run(ws_broadcast(json.dumps(out)))
            except Exception as e:
                print("[ERROR] estimation:", e)
        else:
            pass

        elapsed = time.time() - start
        to_sleep = period - elapsed
        if to_sleep > 0:
            time.sleep(to_sleep)
