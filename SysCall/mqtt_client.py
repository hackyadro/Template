
import paho.mqtt.client as mqtt
import json
import time
import threading
import numpy as np
from collections import deque
from scipy.optimize import minimize
from positioning import (
    rssi_to_distance,
    error_function_weighted,
    update_kalman_filter_1d,
    update_kalman_filter_2d
)

from config import *
# обработчик входящих сообщений
def on_message(client, userdata, msg):
    lock = userdata['lock']
    with lock:
        try:
            beacons_positions = userdata['beacons']
            data_queue = userdata['queue']
            params = userdata['params']
            state = userdata['state']

            raw_rssi_data = json.loads(msg.payload.decode())

            filtered_rssi_map, live_data_update = {}, {}
            for name, rssi in raw_rssi_data.items():
                if name not in beacons_positions:
                    continue

                if name not in state['rssi_history']:
                    state['rssi_history'][name] = deque(maxlen=params['median_window'])
                    state['kalman_states'][name] = {'x': float(rssi), 'P': 1.0}

                # Фильтрация RSSI
                state['rssi_history'][name].append(rssi)
                median_filtered_rssi = np.median(list(state['rssi_history'][name]))
                kalman_state = state['kalman_states'][name]
                new_state, kalman_filtered_rssi = update_kalman_filter_1d(
                    kalman_state, median_filtered_rssi, params['kalman_R_rssi'], params['kalman_Q_rssi']
                )
                state['kalman_states'][name] = new_state
                filtered_rssi_map[name] = kalman_filtered_rssi
                live_data_update[name] = {'raw_rssi': rssi, 'filtered_rssi': round(kalman_filtered_rssi, 2)}

            # Подготовка данных для трилатерации
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

            # Вычисление позиции
            result = minimize(error_function_weighted, state['last_known_position'], args=(beacons_for_calc,),
                              method='L-BFGS-B')

            if result.success:
                calculated_point = np.array(result.x)

                # Фильтр Калмана
                current_time = time.time()
                dt = (current_time - state['last_update_time']) if state['last_update_time'] else 0.1
                state['last_update_time'] = current_time

                if state['position_kalman_state'] is None:
                    state['position_kalman_state'] = {
                        'x': np.array([calculated_point[0], calculated_point[1], 0, 0]), 'P': np.eye(4) * 10.0
                    }
                    filtered_point_coords = tuple(calculated_point)
                else:
                    new_pos_state, filtered_point_coords = update_kalman_filter_2d(
                        state['position_kalman_state'], calculated_point,
                        params['pos_kalman_R'], params['pos_kalman_Q'], dt
                    )
                    state['position_kalman_state'] = new_pos_state

                final_point = {'x': filtered_point_coords[0], 'y': filtered_point_coords[1]}
                state['last_known_position'] = np.array(filtered_point_coords)
                data_queue.put({'point': final_point, 'live_data': live_data_update})

        except Exception as e:
            import traceback
            print(f"Ошибка в MQTT-потоке: {e}")
            traceback.print_exc()

# запуск MQTT клиента
def mqtt_thread_func(beacon_positions, data_queue, params, processing_state):
    lock = threading.Lock()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    client.user_data_set({
        'beacons': beacon_positions,
        'queue': data_queue,
        'params': params,
        'lock': lock,
        'state': processing_state
    })

    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.subscribe(MQTT_TOPIC)
        print("MQTT-поток запущен.")
        client.loop_forever()
    except Exception as e:
        print(f"Не удалось запустить MQTT-поток: {e}")