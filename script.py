import json
import numpy as np
from scipy.optimize import least_squares
import paho.mqtt.client as mqtt
from collections import defaultdict
import time
import matplotlib.pyplot as plt

# Координаты маяков
beacons = {
    'beacon_1': np.array([3.0, -2.4]),
    'beacon_2': np.array([-2.4, -0.6]),
    'beacon_3': np.array([1.8, 9.0]),
    'beacon_4': np.array([4.8, 18.6]),
    'beacon_5': np.array([-1.8, 26.4]),
    'beacon_6': np.array([-1.8, 34.2]),
    'beacon_7': np.array([7.8, 34.2]),
    'beacon_8': np.array([-1.8, 40.8])
}

# Параметры
TX_POWER = -59  # Замените, если известно
MIN_RSSI = -90  # Игнорировать слабые сигналы
AVERAGE_WINDOW = 10  # Количество RSSI для усреднения
UPDATE_INTERVAL = 3  # Секунды между расчётами

# Буфер для усреднения RSSI
rssi_buffer = defaultdict(list)

# Расчёт расстояния по RSSI
def get_distance(rssi, tx_power=TX_POWER):
    if rssi == 0:
        return -1
    ratio = rssi / tx_power
    if ratio < 1.0:
        return ratio ** 10
    else:
        return (0.89976 * (ratio ** 7.7095)) + 0.111

# Функция для least squares
def residuals(params, beacon_positions, distances):
    x, y = params
    calculated_distances = np.sqrt(np.sum((beacon_positions - np.array([x, y]))**2, axis=1))
    return calculated_distances - distances

# Расчёт позиции
def calculate_position(rssi_dict):
    valid_beacons = {k: v for k, v in rssi_dict.items() if v >= MIN_RSSI}
    if len(valid_beacons) < 3:
        return None, "Недостаточно маяков с хорошим сигналом (минимум 3)"
    
    distances = np.array([get_distance(rssi) for rssi in valid_beacons.values()])
    beacon_positions = np.array([beacons[name] for name in valid_beacons.keys()])
    initial_guess = np.mean(beacon_positions, axis=0)
    
    result = least_squares(residuals, initial_guess, args=(beacon_positions, distances))
    if result.success:
        return result.x, None
    return None, "Оптимизация не удалась"

# Визуализация
def plot_position(position):
    plt.clf()
    for name, pos in beacons.items():
        plt.scatter(pos[0], pos[1], label=name, s=100)
    if position is not None:
        plt.scatter(position[0], position[1], color='red', label='Receiver', s=200, marker='x')
    plt.legend()
    plt.grid(True)
    plt.xlabel('X (m)')
    plt.ylabel('Y (m)')
    plt.title('Позиция приёмника и маяков')
    plt.pause(0.1)

# MQTT: обработка входящих сообщений
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print("Полученные данные:", data)
        for beacon in data.get('beacons', []):
            name = beacon.get('name')
            rssi = beacon.get('rssi')
            if name in beacons and rssi is not None:
                print(f"{name}: RSSI={rssi}, TX={beacon.get('tx', 'unknown')}")
                rssi_buffer[name].append(rssi)
                if len(rssi_buffer[name]) > AVERAGE_WINDOW:
                    rssi_buffer[name].pop(0)
                if 'tx' in beacon:
                    rssi_buffer[f"{name}_tx"] = beacon['tx']
    except json.JSONDecodeError:
        print("Ошибка декодирования JSON")

# MQTT: обработка подключения
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Подключено к MQTT")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Ошибка подключения: {reason_code}")

# Расчёт позиции по усреднённым RSSI
def process_position():
    plt.ion()
    while True:
        if rssi_buffer:
            rssi_avg = {beacon: np.mean(rssi_list) for beacon, rssi_list in rssi_buffer.items() if not beacon.endswith('_tx')}
            position, error = calculate_position(rssi_avg)
            if position is not None:
                print(f"Позиция: x={position[0]:.2f}, y={position[1]:.2f}")
                plot_position(position)
            elif error:
                print(f"Ошибка: {error}")
                plot_position(None)
        time.sleep(UPDATE_INTERVAL)

# MQTT настройки
MQTT_BROKER = "193.106.150.201"
MQTT_PORT = 1883
MQTT_TOPIC = "beacons/discovered"

# Подключение к MQTT
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_start()

# Запуск обработки позиций
try:
    process_position()
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()
    plt.close()
    print("Завершено")