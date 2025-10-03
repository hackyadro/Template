import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import threading
import queue
from scipy.optimize import minimize
import numpy as np
import matplotlib.pyplot as plt
from collections import deque


BEACONS_FILE = "standart.beacons"
MQTT_BROKER = "localhost"
MQTT_TOPIC = "registrar/data"


if 'data_queue' not in st.session_state:
    st.session_state.data_queue = queue.Queue()

if 'path' not in st.session_state: st.session_state.path = []
if 'beacons' not in st.session_state: st.session_state.beacons = {}
if 'live_data' not in st.session_state: st.session_state.live_data = {}
if 'recording' not in st.session_state: st.session_state.recording = False
if 'app_initialized' not in st.session_state: st.session_state.app_initialized = False


if 'position_kalman_state' not in st.session_state:
    st.session_state.position_kalman_state = None
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = None

if 'rssi_history' not in st.session_state:
    st.session_state.rssi_history = {}
if 'kalman_states' not in st.session_state:
    st.session_state.kalman_states = {}


st.sidebar.title("Параметры системы")
st.sidebar.markdown("### Шаг 1: Калибровка")
tx_power = st.sidebar.slider("A (Tx Power)", -100.0, -20.0, -56.0, 0.5)
n_path_loss = st.sidebar.slider("n (Path Loss Exponent)", 1.0, 5.0, 2.4, 0.1)

st.sidebar.markdown("### Шаг 2: Фильтры RSSI")
median_window = st.sidebar.slider("Окно медианного фильтра", 3, 70, 12, 1)
kalman_R_rssi = st.sidebar.slider("RSSI - Шум измерения (R)", 0.01, 1.0, 0.8, 0.01)
kalman_Q_rssi = st.sidebar.slider("RSSI - Шум процесса (Q)", 0.0001, 0.1, 0.005, 0.0001)


st.sidebar.markdown("### Шаг 3: Фильтр координат (2D Калман)")

pos_kalman_R = st.sidebar.slider("Координаты - Шум измерения (R)", 0.01, 2.0, 0.5, 0.01)

pos_kalman_Q = st.sidebar.slider("Координаты - Шум процесса (Q)", 0.001, 1.0, 0.1, 0.001)



def load_beacon_positions(filename):
    positions = {}
    try:
        with open(filename, 'r') as f:
            next(f)
            for line in f:
                parts = line.strip().split(';')
                if len(parts) == 3: name, x, y = parts; positions[name] = (float(x), float(y))
        print(f"Загружены маячки из '{filename}': {positions}")
        return positions
    except Exception as e:
        st.error(f"Ошибка загрузки файла '{filename}': {e}")
        return None


def rssi_to_distance(rssi, tx_power_val, n_val):
    return 10 ** ((tx_power_val - rssi) / (10 * n_val))



def error_function_weighted(point_guess, beacons_data):
    error = 0.0
    px, py = point_guess
    for name, (bx, by, distance, weight) in beacons_data.items():
        calculated_dist = np.sqrt((px - bx) ** 2 + (py - by) ** 2)
        error += weight * ((calculated_dist - distance) ** 2)
    return error


def update_kalman_filter_1d(state, measurement, R, Q):
    x_pred = state['x'];
    P_pred = state['P'] + Q
    K = P_pred / (P_pred + R)
    x_new = x_pred + K * (measurement - x_pred);
    P_new = (1 - K) * P_pred
    return {'x': x_new, 'P': P_new}, x_new



def update_kalman_filter_2d(state, measurement, R_val, Q_val, dt):

    F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])

    H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])

    Q = np.eye(4) * Q_val

    R = np.eye(2) * R_val

    x_pred = F @ state['x']
    P_pred = F @ state['P'] @ F.T + Q


    y = measurement - H @ x_pred
    S = H @ P_pred @ H.T + R
    K = P_pred @ H.T @ np.linalg.inv(S)
    x_new = x_pred + K @ y
    P_new = (np.eye(4) - K @ H) @ P_pred

    return {'x': x_new, 'P': P_new}, (x_new[0], x_new[1])



def on_message(client, userdata, msg):
    """Вызывается при получении данных от MQTT. Обрабатывает и фильтрует RSSI."""


    lock = userdata['lock']

    with lock:
        try:
            if 'position_kalman_state' not in st.session_state:
                st.session_state.position_kalman_state = None
            if 'last_update_time' not in st.session_state:
                st.session_state.last_update_time = None
            if 'last_known_position' not in st.session_state:
                st.session_state.last_known_position = np.array([0.0, 0.0])


            if 'rssi_history' not in st.session_state: st.session_state.rssi_history = {}
            if 'kalman_states' not in st.session_state: st.session_state.kalman_states = {}

            beacons_positions = userdata['beacons']
            data_queue = userdata['queue']
            params = userdata['params']
            raw_rssi_data = json.loads(msg.payload.decode())


            filtered_rssi_map, live_data_update = {}, {}
            for name, rssi in raw_rssi_data.items():
                if name not in beacons_positions: continue
                if name not in st.session_state.rssi_history:
                    st.session_state.rssi_history[name] = deque(maxlen=params['median_window'])
                    st.session_state.kalman_states[name] = {'x': float(rssi), 'P': 1.0}
                st.session_state.rssi_history[name].append(rssi)
                median_filtered_rssi = np.median(list(st.session_state.rssi_history[name]))
                kalman_state = st.session_state.kalman_states[name]
                new_state, kalman_filtered_rssi = update_kalman_filter_1d(
                    kalman_state, median_filtered_rssi, params['kalman_R_rssi'], params['kalman_Q_rssi']
                )
                st.session_state.kalman_states[name] = new_state
                filtered_rssi_map[name] = kalman_filtered_rssi
                live_data_update[name] = {'raw_rssi': rssi, 'filtered_rssi': round(kalman_filtered_rssi, 2)}

            beacons_for_calc = {}
            for name, filtered_rssi in filtered_rssi_map.items():
                if name in beacons_positions:
                    distance = rssi_to_distance(filtered_rssi, params['tx_power'], params['n_path_loss'])
                    weight = 1.0 / (distance ** 2 + 0.01)
                    bx, by = beacons_positions[name]
                    beacons_for_calc[name] = (bx, by, distance, weight)

            if len(beacons_for_calc) < 3:
                data_queue.put({'point': None, 'live_data': live_data_update})
                return

            initial_guess = st.session_state.last_known_position
            result = minimize(error_function_weighted, initial_guess, args=(beacons_for_calc,), method='L-BFGS-B')

            if result.success:
                calculated_point = np.array([result.x[0], result.x[1]])
                current_time = time.time()
                dt = (current_time - st.session_state.last_update_time) if st.session_state.last_update_time else 0.1
                st.session_state.last_update_time = current_time

                if st.session_state.position_kalman_state is None:
                    st.session_state.position_kalman_state = {
                        'x': np.array([calculated_point[0], calculated_point[1], 0, 0]),
                        'P': np.eye(4) * 10.0
                    }
                    filtered_point_coords = (calculated_point[0], calculated_point[1])
                else:
                    new_pos_state, filtered_point_coords = update_kalman_filter_2d(
                        st.session_state.position_kalman_state,
                        calculated_point,
                        params['pos_kalman_R'],
                        params['pos_kalman_Q'],
                        dt
                    )
                    st.session_state.position_kalman_state = new_pos_state

                final_point_coords = (filtered_point_coords[0], filtered_point_coords[1])
                final_point = {'x': final_point_coords[0], 'y': final_point_coords[1]}
                st.session_state.last_known_position = np.array(final_point_coords)
                data_queue.put({'point': final_point, 'live_data': live_data_update})

        except Exception as e:
            import traceback
            print(f"Ошибка в MQTT-потоке: {e}")
            traceback.print_exc()


def mqtt_thread_func(beacon_positions, data_queue, params):
    lock = threading.Lock()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    client.user_data_set({
        'beacons': beacon_positions,
        'queue': data_queue,
        'params': params,
        'lock': lock
    })

    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.subscribe(MQTT_TOPIC)
        print("MQTT-поток запущен.")
        client.loop_forever()
    except Exception as e:
        print(f"Не удалось запустить MQTT-поток: {e}")

def format_path_data_for_download(path_data):
    header = "X;Y\n";
    lines = [f"{point['x']};{point['y']}" for point in path_data]
    return header + "\n".join(lines)


st.set_page_config(layout="wide")
st.title("Улучшенная система навигации с фильтрацией")

if not st.session_state.app_initialized:
    st.session_state.beacons = load_beacon_positions(BEACONS_FILE)
    if st.session_state.beacons:
        runtime_params = {
            'tx_power': tx_power, 'n_path_loss': n_path_loss,
            'median_window': median_window,
            'kalman_R_rssi': kalman_R_rssi, 'kalman_Q_rssi': kalman_Q_rssi,
            'pos_kalman_R': pos_kalman_R, 'pos_kalman_Q': pos_kalman_Q
        }
        mqtt_thread = threading.Thread(target=mqtt_thread_func,
                                       args=(st.session_state.beacons, st.session_state.data_queue, runtime_params))
        mqtt_thread.daemon = True
        mqtt_thread.start()
        st.session_state.app_initialized = True
    else:
        st.error("Не удалось загрузить маячки. MQTT-поток не запущен.")

main_col, data_col = st.columns([3, 1])
with main_col:
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    # ...
    with btn_col1:
        if st.button("▶️ Начать новый маршрут", use_container_width=True):
            st.session_state.path = []
            st.session_state.live_data = {}
            st.session_state.rssi_history.clear();
            st.session_state.kalman_states.clear()
            st.session_state.position_kalman_state = None
            st.session_state.last_update_time = time.time()
            st.session_state.last_known_position = np.array([0.0, 0.0])
            st.session_state.recording = True
            st.success("Запись начата!")

    with btn_col2:
        if st.button("⏹️ Завершить маршрут", use_container_width=True):
            st.session_state.recording = False
            st.info("Запись завершена.")
    if not st.session_state.recording and st.session_state.path:
        with btn_col3:
            st.download_button("📥 Скачать маршрут (*.path)", format_path_data_for_download(st.session_state.path),
                               "route.path", use_container_width=True)

    while not st.session_state.data_queue.empty():
        data = st.session_state.data_queue.get()
        if data.get('live_data'): st.session_state.live_data.update(data['live_data'])
        if data.get('point') and st.session_state.recording: st.session_state.path.append(data['point'])

    fig, ax = plt.subplots(figsize=(10, 8))
    path_copy = list(st.session_state.path)
    if st.session_state.beacons:
        bx = [p[0] for p in st.session_state.beacons.values()];
        by = [p[1] for p in st.session_state.beacons.values()]
        ax.scatter(bx, by, s=120, c='blue', label='Маячки', zorder=10)
        for name, pos in st.session_state.beacons.items():
            ax.text(pos[0], pos[1] + 0.3, name, fontsize=12, color='darkblue', ha='center')
            if name in st.session_state.live_data:
                ax.text(pos[0], pos[1] - 1.2, f"RSSI: {st.session_state.live_data[name]['filtered_rssi']}", fontsize=9,
                        color='gray', ha='center')
    if len(path_copy) > 0:
        px = [p['x'] for p in path_copy];
        py = [p['y'] for p in path_copy]
        ax.plot(px, py, color='green', marker='o', linestyle='-', markersize=4, label="Пройденный путь")
        ax.scatter(px[-1], py[-1], s=180, c='red', edgecolors='black', zorder=5, label='Текущая позиция')
    ax.set_title("Карта");
    ax.set_xlabel("X (м)");
    ax.set_ylabel("Y (м)")
    ax.grid(True);
    ax.legend();
    ax.axis('equal')
    st.pyplot(fig, clear_figure=True)

with data_col:
    st.subheader("Текущие данные")
    st.dataframe(st.session_state.live_data, use_container_width=True)
    st.subheader("Последние точки пути")
    st.dataframe(path_copy[-10:], use_container_width=True)

time.sleep(0.5)
st.rerun()