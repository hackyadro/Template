import numpy as np


BEACONS = {
    "beacon_1": (3.0, -2.4),
    "beacon_2": (-2.4, -0.6),
    "beacon_3": (1.8, 9.0),
    "beacon_4": (4.8, 18.6),
    "beacon_5": (-1.8, 26.4),
    "beacon_6": (-1.8, 34.2),
    "beacon_7": (7.8, 34.2),
    "beacon_8": (-1.8, 40.8),
}


RSSI0 = {b: -59 for b in BEACONS}  
N = {b: 2.0 for b in BEACONS}      
SIGMA_RSSI = {b: 3.0 for b in BEACONS} 

ln10 = np.log(10)


def rssi_to_distance(rssi, rssi0, n):
    return 10 ** ((rssi0 - rssi) / (10.0 * n))


def var_distance_from_rssi(d, n, sigma_rssi):
    fac = (d * ln10 / (10.0 * n))
    return (fac**2) * (sigma_rssi**2)


def robust_wls(rssi_dict):
    """
    rssi_dict = {"beacon_1": -70, "beacon_2": -80, ...}
    Возвращает (x,y), ковариацию (2x2)
    """
    beacons = []
    dists = []
    vars_ = []

    for b, rssi in rssi_dict.items():
        if b not in BEACONS:
            continue
        d = rssi_to_distance(rssi, RSSI0[b], N[b])
        var_d = var_distance_from_rssi(d, N[b], SIGMA_RSSI[b])
        beacons.append(BEACONS[b])
        dists.append(d)
        vars_.append(var_d)

    beacons = np.array(beacons)
    dists = np.array(dists)
    vars_ = np.array(vars_)

    if len(beacons) < 3:
        return None, None

    idx_sort = np.argsort(dists)
    sel_idx = list(idx_sort[:3])
    if len(idx_sort) > 3:
        sel_idx.append(idx_sort[-1])

    beacons = beacons[sel_idx]
    dists = dists[sel_idx]
    vars_ = vars_[sel_idx]

    x = np.mean(beacons[:, 0])
    y = np.mean(beacons[:, 1])

    for _ in range(10):
        A = []
        b = []
        for (bx, by), di in zip(beacons, dists):
            r_est = np.sqrt((x - bx) ** 2 + (y - by) ** 2)
            if r_est < 1e-6:
                r_est = 1e-6
            A.append([(x - bx) / r_est, (y - by) / r_est])
            b.append(di - r_est)

        A = np.array(A)
        b = np.array(b)

        w = 1.0 / vars_
        sigma = np.std(b) if np.std(b) > 1e-3 else 1.0
        c = 1.5 * sigma
        for i in range(len(b)):
            if abs(b[i]) > c:
                w[i] *= c / abs(b[i])

        W = np.diag(w)
        AtW = A.T @ W
        H = AtW @ A
        g = AtW @ b

        try:
            dx = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break

        x += dx[0]
        y += dx[1]

        if np.linalg.norm(dx) < 1e-3:
            break

    cov = np.linalg.inv(H)
    return (x, y), cov


class EKF:
    def __init__(self, dt=0.1):
        self.dt = dt
        self.x = np.zeros((4, 1))
        self.P = np.eye(4) * 100.0

        self.Q = np.diag([0.1, 0.1, 1.0, 1.0])
        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]])
        self.R = np.eye(2) * 2.0

    def predict(self):
        dt = self.dt
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self.Q

    def update(self, z, R=None):
        if R is not None:
            self.R = R
        y = z.reshape(2, 1) - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P

    def get_state(self):
        return self.x[0, 0], self.x[1, 0]


ekf = EKF(dt=0.1)

def locate_from_rssi(rssi_dict):
    ekf.predict()
    pos, cov = robust_wls(rssi_dict)
    if pos is not None:
        R = cov if cov is not None else np.eye(2) * 5.0
        ekf.update(np.array(pos), R=R)
    return ekf.get_state()
