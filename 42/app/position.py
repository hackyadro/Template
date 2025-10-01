# positioning.py
import numpy as np

def rssi_to_distance(rssi, A=-59.0, n=2.2):
    # A = RSSI на 1 м; n = показатель затухания среды
    return 10 ** ((A - rssi) / (10.0 * n))

def trilaterate_wls(beacon_xy, distances):
    """
    beacon_xy: list[(x,y)] длины >=3
    distances: list[d]      той же длины
    Возвращает (x,y)
    """
    if len(beacon_xy) < 3:
        raise ValueError("Нужно >=3 маяков")

    # опорный маяк N (последний)
    (xN, yN), dN = beacon_xy[-1], distances[-1]
    A = []
    b = []
    w = []
    for (xi, yi), di in zip(beacon_xy[:-1], distances[:-1]):
        A.append([2*(xi - xN), 2*(yi - yN)])
        b.append([dN**2 - di**2 + xi**2 - xN**2 + yi**2 - yN**2])
        w.append(1.0 / max(di, 1e-3)**2)  # вес: ближним доверяем больше

    A = np.asarray(A, float)
    b = np.asarray(b, float)
    W = np.diag(w)
    AtW = A.T @ W
    x = np.linalg.lstsq(AtW @ A, AtW @ b, rcond=None)[0].ravel()
    return float(x[0]), float(x[1])

def estimate_xy(beacons, rssi_by_name, A_by=None, n_by=None, top_k=6):
    """
    beacons: dict name -> (x,y)
    rssi_by_name: dict name -> rssi (средний по окну)
    A_by: dict name -> A_i (RSSI@1м); по умолчанию -59
    n_by: dict name -> n_i; по умолчанию 2.2
    top_k: берём K сильнейших (по RSSI)
    """
    A_by = A_by or {}
    n_by = n_by or {}

    # сортируем по сильному сигналу
    pairs = sorted(rssi_by_name.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

    pts, ds = [], []
    for name, rssi in pairs:
        if name not in beacons:
            continue
        x, y = beacons[name]
        A = A_by.get(name, -59.0)
        n = n_by.get(name, 2.2)
        d = rssi_to_distance(rssi, A, n)
        pts.append((x, y))
        ds.append(d)

    if len(pts) < 3:
        raise ValueError("Недостаточно маяков для трилатерации")

    return trilaterate_wls(pts, ds)
