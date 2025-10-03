import os
import csv
import math
from dataclasses import dataclass
from typing import Optional, List

import numpy as np

# -----------------------------
# paths
# -----------------------------
CUR_DIR = os.path.dirname(os.path.realpath(__file__))
STATIONS_PATH = os.path.join(CUR_DIR, "data", "beacons.txt")

ln10 = np.log(10)

# -----------------------------
# dataclasses
# -----------------------------
@dataclass
class Position:
    x: float
    y: float

@dataclass
class StationRssi:
    name: str
    rssi: float

# -----------------------------
# constants
# -----------------------------
RSSI0 = {}
N = {}
SIGMA_RSSI = {}
BEACONS = {}

# -----------------------------
# file/stations
# -----------------------------
def check_stations_path() -> bool:
    return os.path.exists(STATIONS_PATH)

def load_stations() -> dict[str, Position]:
    stations: dict[str, Position] = {}
    if not check_stations_path():
        return stations
    with open(STATIONS_PATH, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        for row in reader:
            name = row["Name"]
            x = float(row["X"])
            y = float(row["Y"])
            stations[name] = Position(x, y)
            BEACONS[name] = (x, y)
            RSSI0[name] = -59
            N[name] = 2.0
            SIGMA_RSSI[name] = 3.0
    return stations

# -----------------------------
# distance calculations
# -----------------------------
def rssi_to_distance(rssi: float, rssi0: float, n: float) -> float:
    return 10 ** ((rssi0 - rssi) / (10.0 * n))

def var_distance_from_rssi(d: float, n: float, sigma_rssi: float) -> float:
    fac = (d * ln10 / (10.0 * n))
    return (fac ** 2) * (sigma_rssi ** 2)

# -----------------------------
# robust WLS
# -----------------------------
def robust_wls(rssi_dict: dict[str, float]) -> tuple[Optional[Position], Optional[np.ndarray]]:
    stations_pos = load_stations()
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
        b_vec = []
        for (bx, by), di in zip(beacons, dists):
            r_est = math.hypot(x - bx, y - by)
            if r_est < 1e-6:
                r_est = 1e-6
            A.append([(x - bx) / r_est, (y - by) / r_est])
            b_vec.append(di - r_est)

        A = np.array(A)
        b_vec = np.array(b_vec)

        w = 1.0 / vars_
        sigma = np.std(b_vec) if np.std(b_vec) > 1e-3 else 1.0
        c = 1.5 * sigma
        for i in range(len(b_vec)):
            if abs(b_vec[i]) > c:
                w[i] *= c / abs(b_vec[i])

        W = np.diag(w)
        AtW = A.T @ W
        H = AtW @ A
        g = AtW @ b_vec

        try:
            dx = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break

        x += dx[0]
        y += dx[1]

        if np.linalg.norm(dx) < 1e-3:
            break

    cov = np.linalg.inv(H)
    return Position(x, y), cov

# -----------------------------
# EKF
# -----------------------------
class EKF:
    def __init__(self, dt: float = 0.1):
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

    def update(self, z: np.ndarray, R: np.ndarray = None):
        if R is not None:
            self.R = R
        y = z.reshape(2, 1) - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P

    def get_state(self) -> tuple[float, float]:
        return float(self.x[0, 0]), float(self.x[1, 0])

ekf = EKF(dt=0.1)

# -----------------------------
# locate
# -----------------------------
def locate_from_rssi(rssi_dict: dict[str, float]) -> tuple[float, float]:
    ekf.predict()
    pos, cov = robust_wls(rssi_dict)
    if pos is not None:
        R = cov if cov is not None else np.eye(2) * 5.0
        ekf.update(np.array([pos.x, pos.y]), R=R)
    return ekf.get_state()

def get_board_pos(data: List[StationRssi]) -> Optional[Position]:
    if len(data) < 3:
        return None
    rssi_dict = {s.name: s.rssi for s in data}
    x, y = locate_from_rssi(rssi_dict)
    return Position(x, y)
