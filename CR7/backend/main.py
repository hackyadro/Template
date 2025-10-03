import time
import threading
from statistics import median
from beacons import BEACON_POSITIONS
from trilateration import RobustTrilateration
from mqtt_handler import init_mqtt, get_smoothed_rssi, stop_mqtt
from config import WINDOW_SEC
import state
import api

def get_smoothed_rssi_from_handler():
    return get_smoothed_rssi()

def main_loop():
    client = init_mqtt()
    trilaterator = RobustTrilateration(use_kalman=True)

    if not BEACON_POSITIONS:
        print("ВНИМАНИЕ: Список маяков пуст. Проверь файл standart.beacons в корне проекта.")
    else:
        print(f"Загружено маяков: {len(BEACON_POSITIONS)}")

    print("Собираем данные... (Ctrl-C для остановки)")

    try:
        while True:
            start = time.time()
            while time.time() - start < WINDOW_SEC:
                time.sleep(0.03)

            smoothed_rssi = get_smoothed_rssi_from_handler()

            points = []
            rssi_values = []

            for name, rssi in smoothed_rssi.items():
                if rssi is not None and name in BEACON_POSITIONS:
                    points.append(BEACON_POSITIONS[name])
                    rssi_values.append(rssi)

            if len(points) >= 3:
                result = trilaterator.trilaterate_improved(points, rssi_values, dt=WINDOW_SEC)

                # сохраняем последнюю позицию для API
                try:
                    state.save_last_position(result)
                except Exception as e:
                    print("Ошибка при сохранении позиции:", e)
            

                print("=== Позиция ===")
                print(f"Координаты: ({result['x']:.2f}, {result['y']:.2f})")
                print(f"Точность (оценка): ±{result['accuracy_estimate']:.2f} м")
                eq = result.get('environment_quality', {})
                print(f"Качество: {eq.get('quality')} | Стабильность: {eq.get('stability')}")
                print(f"Антенн использовано: {result['anchors_used']}")
                if eq.get('median_rssi') is not None:
                    print(f"Медиана RSSI: {eq.get('median_rssi'):.1f} dBm")
                print()
            else:
                print(f"Недостаточно маяков ({len(points)}), ждём дальше...")

    except KeyboardInterrupt:
        print("Остановка...")
    finally:
        stop_mqtt()
        print("MQTT остановлен.")

if __name__ == "__main__":
    # Запускаем API в отдельном потоке
    api_thread = threading.Thread(target=api.run_api, daemon=True)
    api_thread.start()

    # Запускаем основной цикл
    main_loop()