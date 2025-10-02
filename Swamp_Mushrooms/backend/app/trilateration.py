import numpy as np
from typing import Dict, List, Tuple

# convert RSSI to distance using log-distance path loss model
def rssi_to_distance(rssi: float, p_tx: float=-59.0, n: float=2.5) -> float:
    """
    p_tx: reference RSSI at 1 meter (dBm). Tune for your beacons.
    n: path-loss exponent (2..4). Tune per environment.
    """
    # d = 10^((Ptx - RSSI) / (10 * n))
    return 10 ** ((p_tx - rssi) / (10.0 * n))

def trilateration(anchors: Dict[str, Tuple[float,float]],
                  measurements: List[Dict],
                  p_tx: float=-59.0, n: float=2.5) -> Tuple[float,float]:
    """
    anchors: mapping anchor_id -> (x,y)
    measurements: list of {"beacon_id","rssi"}
    returns estimated (x,y)
    """
    # need at least 3 anchors
    if len(measurements) < 3:
        raise ValueError("Need at least 3 anchors for trilateration")

    xs = []
    ys = []
    ds = []
    for m in measurements:
        aid = m["beacon_id"]
        rssi = m["rssi"]
        if aid not in anchors:
            continue
        x,y = anchors[aid]
        d = rssi_to_distance(rssi, p_tx=p_tx, n=n)
        xs.append(x); ys.append(y); ds.append(d)

    # build linearized system: (xi^2+yi^2 - ri^2) - (x1^2+y1^2 - r1^2) = 2*(xi-x1)*x + 2*(yi-y1)*y
    A=[]
    b=[]
    x1,y1,r1 = xs[0], ys[0], ds[0]
    for xi, yi, ri in zip(xs[1:], ys[1:], ds[1:]):
        A.append([2*(xi - x1), 2*(yi - y1)])
        b.append((xi**2+yi**2 - ri**2) - (x1**2+y1**2 - r1**2))
    A = np.array(A)
    b = np.array(b)
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        return float(sol[0]), float(sol[1])
    except Exception as e:
        raise RuntimeError("Trilateration failed: " + str(e))
