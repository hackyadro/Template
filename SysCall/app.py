import streamlit as st
import queue
import threading
import time
import numpy as np
import matplotlib.pyplot as plt

from config import BEACONS_FILE
from utils import load_beacon_positions, format_path_data_for_download
from mqtt_client import mqtt_thread_func


def initialize_session_state():
    if 'data_queue' not in st.session_state:
        st.session_state.data_queue = queue.Queue()
    if 'path' not in st.session_state:
        st.session_state.path = []
    if 'beacons' not in st.session_state:
        st.session_state.beacons = {}
    if 'live_data' not in st.session_state:
        st.session_state.live_data = {}
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = False


initialize_session_state()


st.set_page_config(layout="wide")
st.title("Навигация по BLE-маячкам")

# Боковая панель с настройками
st.sidebar.title("Параметры системы")
st.sidebar.markdown("### Шаг 1: Калибровка")
tx_power = st.sidebar.slider("A (Tx Power)", -100.0, -20.0, -56.0, 0.5)
n_path_loss = st.sidebar.slider("n (Path Loss Exponent)", 1.0, 5.0, 2.4, 0.1)

st.sidebar.markdown("### Шаг 2: Фильтры RSSI")
median_window = st.sidebar.slider("Окно медианного фильтра", 3, 70, 9, 1)
kalman_R_rssi = st.sidebar.slider("RSSI - Шум измерения (R)", 0.01, 1.0, 0.8, 0.01)
kalman_Q_rssi = st.sidebar.slider("RSSI - Шум процесса (Q)", 0.0001, 0.1, 0.005, 0.0001)

st.sidebar.markdown("### Шаг 3: Фильтр координат (2D Калман)")
pos_kalman_R = st.sidebar.slider("Координаты - Шум измерения (R)", 0.01, 2.0, 0.5, 0.01)
pos_kalman_Q = st.sidebar.slider("Координаты - Шум процесса (Q)", 0.001, 1.0, 0.1, 0.001)


if not st.session_state.app_initialized:
    st.session_state.beacons = load_beacon_positions(BEACONS_FILE)
    if st.session_state.beacons:
        runtime_params = {
            'tx_power': tx_power, 'n_path_loss': n_path_loss,
            'median_window': median_window,
            'kalman_R_rssi': kalman_R_rssi, 'kalman_Q_rssi': kalman_Q_rssi,
            'pos_kalman_R': pos_kalman_R, 'pos_kalman_Q': pos_kalman_Q
        }

        processing_state = {
            'position_kalman_state': None, 'last_update_time': None,
            'last_known_position': np.array([0.0, 0.0]),
            'rssi_history': {}, 'kalman_states': {}
        }

        mqtt_thread = threading.Thread(
            target=mqtt_thread_func,
            args=(st.session_state.beacons, st.session_state.data_queue, runtime_params, processing_state)
        )
        mqtt_thread.daemon = True
        mqtt_thread.start()
        st.session_state.app_initialized = True
    else:
        st.error("Не удалось загрузить маячки. MQTT-поток не запущен.")


main_col, data_col = st.columns([3, 1])

with main_col:
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    if btn_col1.button("▶️ Начать новый маршрут"):
        st.session_state.path = []
        st.session_state.live_data = {}
        st.session_state.recording = True
        st.success("Запись начата!")
        st.rerun()

    if btn_col2.button("⏹️ Завершить маршрут"):
        st.session_state.recording = False
        st.info("Запись завершена.")
        st.rerun()

    if not st.session_state.recording and st.session_state.path:
        btn_col3.download_button(
            "📥 Скачать маршрут (*.path)",
            format_path_data_for_download(st.session_state.path),
            "route.path"
        )


    while not st.session_state.data_queue.empty():
        data = st.session_state.data_queue.get()
        if data.get('live_data'):
            st.session_state.live_data.update(data['live_data'])
        if data.get('point') and st.session_state.recording:
            st.session_state.path.append(data['point'])

    # карта
    fig, ax = plt.subplots(figsize=(10, 8))
    path_copy = list(st.session_state.path)

    # Маячки
    if st.session_state.beacons:
        bx = [p[0] for p in st.session_state.beacons.values()]
        by = [p[1] for p in st.session_state.beacons.values()]
        ax.scatter(bx, by, s=120, c='blue', label='Маячки', zorder=10)
        for name, pos in st.session_state.beacons.items():
            ax.text(pos[0], pos[1] + 0.3, name, fontsize=12, color='darkblue', ha='center')
            if name in st.session_state.live_data and 'filtered_rssi' in st.session_state.live_data[name]:
                ax.text(pos[0], pos[1] - 1.2, f"RSSI: {st.session_state.live_data[name]['filtered_rssi']}", fontsize=9,
                        color='gray', ha='center')

    # Путь
    if len(path_copy) > 0:
        px = [p['x'] for p in path_copy]
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
    st.dataframe(st.session_state.live_data)
    st.subheader("Последние точки пути")
    st.dataframe(path_copy[-10:])


time.sleep(0.4)
st.rerun()