import math
from collections import defaultdict, deque

ALPHA = 0.15
RSSI_FILT = {}
RSSI_HISTORY = defaultdict(lambda: deque(maxlen=50))  # ~50 пакетов

def rssi_to_distance(rssi, tx_power, n):
    return 10 ** ((tx_power - rssi) / (10.0 * n))

def smooth_rssi(bid, rssi):
    """Экспоненциальное сглаживание RSSI"""
    if bid not in RSSI_FILT:
        RSSI_FILT[bid] = rssi
    else:
        RSSI_FILT[bid] = ALPHA * rssi + (1 - ALPHA) * RSSI_FILT[bid]
    return RSSI_FILT[bid]

def add_rssi_sample(bid, rssi):
    """Добавляем сырое значение в историю"""
    RSSI_HISTORY[bid].append(rssi)

def adaptive_variance(bid):
    """Считаем дисперсию на основе истории RSSI"""
    history = list(RSSI_HISTORY[bid])
    if len(history) > 5:
        mean_rssi = sum(history) / len(history)
        var = sum((x - mean_rssi) ** 2 for x in history) / (len(history) - 1)
    else:
        var = 4.0
    return max(1.0, var)
