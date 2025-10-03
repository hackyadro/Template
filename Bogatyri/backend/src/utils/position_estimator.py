import numpy as np
from scipy.optimize import minimize


def trilateration_error(point, beacons, distances):
    x, y = point
    error = 0.0
    for (xb, yb), r in zip(beacons, distances):
        dist_calculated = np.sqrt((x - xb) ** 2 + (y - yb) ** 2)
        error += (dist_calculated - r) ** 2
    return error


def rssi_to_distance(rssi: int, rssi0: int = 40, n: float = 2.0):
    """
    Преобразует RSSI в расстояние по логарифмической модели затухания сигнала

    Parameters:
    rssi: измеренная сила сигнала
    rssi0: RSSI на расстоянии 1 метр (калибровочная константа)
    n: коэффициент затухания (2 для свободного пространства, 2-4 для помещений)
    """
    return 10 ** ((rssi0 - rssi) / (10 * n))


def cords_estimator_from_rssi(
        beacons_with_rssi: list[tuple[float, float, int]],
        rssi0: int = 40,
        n: float = 2.0
) -> tuple[float, float]:
    """
    Оценивает координаты на основе RSSI маяков

    Parameters:
    beacons_with_rssi: список кортежей (x, y, rssi) для каждого маяка
    rssi0: RSSI на расстоянии 1 метр
    n: коэффициент затухания сигнала

    Returns:
    tuple: estimated (x, y) coordinates
    """
    rssi = [rssi_val for x, y, rssi_val in beacons_with_rssi]
    mean_rssi = np.mean(rssi, axis=0)
    beacons = [(x, y) for x, y, rssi_val in beacons_with_rssi if rssi_val <= mean_rssi]
    distances = [rssi_to_distance(rssi_val, rssi0, n) for x, y, rssi_val in beacons_with_rssi if rssi_val <= mean_rssi]

    initial_guess = np.mean(beacons, axis=0)

    result = minimize(
        trilateration_error,
        initial_guess,
        args=(beacons, distances),
        method='Powell'
    )

    if result.success:
        return result.x
    else:
        raise RuntimeError(f"Optimization failed: {result.message}")

print(cords_estimator_from_rssi([(0.0, 0.0, 81),(3.0, 9.0, 80), (19.0, 2.0, 65), (34.0, -3.0, 74), (47.0, 8.0, 42), (60.0, 8.0, 60), (60.0, -8.0, 76), (71.0, 8.0, 63)], n=2.0))