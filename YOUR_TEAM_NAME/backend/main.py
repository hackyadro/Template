import time
from config import WINDOW_SEC, BEACONS_FILE
from beacons import load_beacons_from_csv
from trilateration import RobustTrilateration, estimate_distance, trilaterate_least_squares
from mqtt_handler import init_mqtt, get_smoothed_rssi, ANCHOR_POINTS

# Загружаем маяки
ANCHOR_POINTS.update(load_beacons_from_csv(BEACONS_FILE))

# Инициализируем трилатерацию и MQTT
trilaterator = RobustTrilateration()
client = init_mqtt()

print("Собираем данные...")

try:
    while True:
        start = time.time()
        while time.time() - start < WINDOW_SEC:
            time.sleep(0.05)

        smoothed_rssi = get_smoothed_rssi()
        distances_old, points, rssi_values = [], [], []

        for name, rssi in smoothed_rssi.items():
            if rssi is not None and name in ANCHOR_POINTS:
                distances_old.append(estimate_distance(rssi))
                points.append(ANCHOR_POINTS[name])
                rssi_values.append(rssi)

        if len(points) >= 3:
            pos_old = trilaterate_least_squares(points, distances_old)
            result = trilaterator.trilaterate_improved(points, rssi_values)
            pos_new = (result['x'], result['y'])

            print(f"=== Позиция ===")
            print(f"Старый алгоритм: ({pos_old[0]:.2f}, {pos_old[1]:.2f})")
            print(f"Новый алгоритм:  ({pos_new[0]:.2f}, {pos_new[1]:.2f})")
            print(f"Точность: ±{result['accuracy_estimate']:.1f} м")
            print(f"Качество: {result['environment_quality']['quality']}")
            print(f"Стабильность: {result['environment_quality']['stability']}")
            print(f"Антенн использовано: {result['anchors_used']}")
            print(f"Медиана RSSI: {result['environment_quality']['median_rssi']:.1f} dBm\n")
        else:
            print(f"Недостаточно маяков ({len(points)}), ждём дальше...")

except KeyboardInterrupt:
    print("Остановка...")
    client.loop_stop()
    client.disconnect()