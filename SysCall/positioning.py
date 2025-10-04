
import numpy as np
from scipy.optimize import minimize

# RSSI в метры
def rssi_to_distance(rssi, tx_power, n_path_loss):
    return 10 ** ((tx_power - rssi) / (10 * n_path_loss))


def error_function_weighted(point_guess, beacons_data):

    error = 0.0
    px, py = point_guess
    for name, (bx, by, distance, weight) in beacons_data.items():
        calculated_dist = np.sqrt((px - bx) ** 2 + (py - by) ** 2)
        error += weight * ((calculated_dist - distance) ** 2)
    return error

# 1D фильтр Калмана
def update_kalman_filter_1d(state, measurement, R, Q):
    x_pred = state['x']
    P_pred = state['P'] + Q

    K = P_pred / (P_pred + R)
    x_new = x_pred + K * (measurement - x_pred)
    P_new = (1 - K) * P_pred

    return {'x': x_new, 'P': P_new}, x_new

# 2D
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