# backend/main.py
import time
from statistics import median
from beacons import BEACON_POSITIONS
from trilateration import RobustTrilateration
from mqtt_handler import stop_mqtt, rssi_history
from config import WINDOW_SEC
import state   # <--- добавили

trilaterator = RobustTrilateration()


def get_smoothed_rssi():
    """Возвращает сглаженные значения RSSI используя медиану"""
    smoothed = {}
    for name, history in rssi_history.items():
        if history:
            smoothed[name] = median(history)
    return smoothed


def main_loop():
    print("Собираем данные...")

    try:
        while True:
            start = time.time()
            # ждём окно
            while time.time() - start < WINDOW_SEC:
                time.sleep(0.05)

            smoothed_rssi = get_smoothed_rssi()

            points = []
            rssi_values = []

            for name, rssi in smoothed_rssi.items():
                if rssi is not None and name in BEACON_POSITIONS:
                    points.append(BEACON_POSITIONS[name])
                    rssi_values.append(rssi)

            if len(points) >= 3:
                result = trilaterator.trilaterate_improved(points, rssi_values)
                pos_new = (result['x'], result['y'])

                # сохраняем последнюю позицию в state
                state.last_position = result

                print(f"=== Позиция ===")
                print(f"Координаты: ({pos_new[0]:.2f}, {pos_new[1]:.2f})")
                print(f"Точность: ±{result['accuracy_estimate']:.1f} м")
                print(f"Качество: {result['environment_quality']['quality']}")
                print(f"Стабильность: {result['environment_quality']['stability']}")
                print(f"Антенн использовано: {result['anchors_used']}")
                print(f"Медиана RSSI: {result['environment_quality']['median_rssi']:.1f} dBm")
                print()

            else:
                print(f"Недостаточно маяков ({len(points)}), ждём дальше...")

    except KeyboardInterrupt:
        print("Остановка...")
    finally:
        stop_mqtt()
        print("MQTT остановлен.")

if __name__ == "__main__":
    main_loop()