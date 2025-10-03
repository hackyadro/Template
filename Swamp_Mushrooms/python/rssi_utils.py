from config import RSSI_FILT, ALPHA

def rssi_to_distance(rssi, tx_power, n):
    """Перевод RSSI в расстояние"""
    return 10 ** ((tx_power - rssi) / (10.0 * n))

def smooth_rssi(bid, rssi):
    """Экспоненциальное сглаживание RSSI"""
    if bid not in RSSI_FILT:
        RSSI_FILT[bid] = rssi
    else:
        RSSI_FILT[bid] = ALPHA * rssi + (1 - ALPHA) * RSSI_FILT[bid]
    return RSSI_FILT[bid]
