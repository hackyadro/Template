import json
import time
import math
import numpy as np
from collections import defaultdict
from scipy.optimize import least_squares
import paho.mqtt.client as mqtt

# --- Конфигурация ---
MQTT_SERVER = "10.49.206.215"
MQTT_PORT   = 1883
MQTT_TOPIC  = "beacons/#"
WINDOW_SEC  = 1.0  # окно сбора данных

# Координаты маяков (пример, нужно заменить на реальные)
ANCHOR_POINTS = {
    "beacon_1": (3.0, -2.4),
    "beacon_2": (-2.4, -0.6),
    "beacon_3": (1.8, 9),
    "beacon_4": (4.8, 18.6),
    "beacon_5": (-1.8, 26.4),
    "beacon_6": (-1.8, 34.2),
    "beacon_7": (7.8, 34.2),
    "beacon_8": (-1.8, 40.8),
}

# --- Алгоритмы ---
def estimate_distance(rssi, measured_power=-69, environmental_factor=2):
    return 10 ** ((measured_power - rssi) / (10 * environmental_factor))

def trilaterate_least_squares(anchor_points, distances):
    def residuals(params, anchor_points, distances):
        x, y = params
        residual = []
        for i, point in enumerate(anchor_points):
            calc_dist = math.sqrt((x - point[0])**2 + (y - point[1])**2)
            residual.append(calc_dist - distances[i])
        return residual

    initial_guess = [np.mean([p[0] for p in anchor_points]),
                     np.mean([p[1] for p in anchor_points])]
    result = least_squares(residuals, initial_guess, args=(anchor_points, distances), method='lm')
    return result.x[0], result.x[1]

# --- Хранение последних RSSI ---
latest_rssi = defaultdict(lambda: None)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        name = payload.get("name")
        rssi = payload.get("rssi")
        if name and name in ANCHOR_POINTS:
            latest_rssi[name] = rssi
    except Exception as e:
        print("Ошибка парсинга:", e)

# --- MQTT ---
client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_SERVER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

print("Собираем данные...")

# --- Основной цикл ---
try:
    while True:
        start = time.time()
        # ждём окно
        while time.time() - start < WINDOW_SEC:
            time.sleep(0.05)

        # забираем данные за окно
        distances = []
        points = []
        for name, rssi in latest_rssi.items():
            if rssi is not None and name in ANCHOR_POINTS:
                distances.append(estimate_distance(rssi))
                points.append(ANCHOR_POINTS[name])

        if len(distances) >= 3:
            pos = trilaterate_least_squares(points, distances)
            print(f"Позиция: ({pos[0]:.2f}, {pos[1]:.2f}), данные от {len(distances)} маяков")
        else:
            print(f"Недостаточно маяков ({len(distances)}), ждём дальше...")

except KeyboardInterrupt:
    print("Остановка...")
    client.loop_stop()
    client.disconnect()