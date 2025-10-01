from typing import List, Dict, Any, Tuple
import math
import numpy as np


class Kalman1D:
    """Простой 1D Калман для сглаживания"""
    def __init__(self, q: float = 0.1, r: float = 0.5):
        self.x = 0.0
        self.P = 1.0
        self.Q = q  # process noise
        self.R = r  # measurement noise
        self.initialized = False

    def update(self, measurement: float) -> float:
        if not self.initialized:
            self.x = measurement
            self.initialized = True

        # prediction
        self.P = self.P + self.Q
        # update
        K = self.P / (self.P + self.R)
        self.x = self.x + K * (measurement - self.x)
        self.P = (1 - K) * self.P
        return self.x


class Kalman2D:
    def __init__(self, q: float = 0.05, r: float = 0.3):
        self.fx = Kalman1D(q, r)
        self.fy = Kalman1D(q, r)

    def update(self, x: float, y: float) -> Tuple[float, float]:
        return self.fx.update(x), self.fy.update(y)


class PositioningService:
    """
    Алгоритмы: перевод RSSI->distance (логарифмическая модель) + линейная трилатерация (наименьшие квадраты) + Калман
    """

    def __init__(self, path_loss_n: float = 2.2, default_tx: int = -59):
        self.path_loss_n = path_loss_n
        self.default_tx = default_tx
        # фильтры на уровне сессии держим снаружи (в SessionManager)

    def rssi_to_distance(self, rssi: float, tx_power: float) -> float:
        """
        Модель log-distance path loss:
        d = 10 ^ ((txPower - RSSI) / (10 * n))
        """
        n = self.path_loss_n
        return 10 ** ((tx_power - rssi) / (10 * n))

    def calculate_position(self, readings: List[Dict[str, Any]], beacons: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        readings: [{'beaconId','rssi'}, ...]
        beacons: [{'id','x','y','z','txPower'}, ...]
        Возвращает {'x','y','accuracy'}
        """
        if not readings or not beacons:
            raise ValueError("No readings or beacons")

        # карта маяков
        bmap = {b["id"]: b for b in beacons}

        # оставим только те ридинги, для которых есть конфиг
        usable = [r for r in readings if r["beaconId"] in bmap]

        if len(usable) < 3:
            # минимум 3 маяка для 2D
            raise ValueError("At least 3 beacons required for trilateration")

        # возьмём топ-4 по силе сигнала (чем ближе к 0, тем лучше)
        usable.sort(key=lambda r: r["rssi"], reverse=True)  # -50 лучше, чем -80
        top = usable[:4] if len(usable) > 4 else usable

        pts = []
        dists = []
        for r in top:
            b = bmap[r["beaconId"]]
            tx = b.get("txPower", self.default_tx)
            d = self.rssi_to_distance(r["rssi"], tx)
            pts.append((b["x"], b["y"]))
            dists.append(d)

        x, y = self._least_squares_trilateration(pts, dists)
        # оценка точности — rmse по разнице фактических расстояний до точек
        rmse = self._rmse((x, y), pts, dists)
        return {"x": float(x), "y": float(y), "accuracy": float(rmse)}

    def _least_squares_trilateration(self, pts: List[Tuple[float, float]], dists: List[float]) -> Tuple[float, float]:
        """
        Линеаризуем уравнение и решаем A x = b МНК.
        Берём первый маяк как опорный.
        """
        if len(pts) < 3:
            raise ValueError("Need >=3 points")

        (x1, y1) = pts[0]
        d1 = dists[0]

        A = []
        b = []
        for (xi, yi), di in zip(pts[1:], dists[1:]):
            A.append([2 * (xi - x1), 2 * (yi - y1)])
            b.append(di ** 2 - d1 ** 2 - xi ** 2 + x1 ** 2 - yi ** 2 + y1 ** 2)

        A = np.array(A, dtype=float)
        b = np.array(b, dtype=float).reshape(-1, 1)

        # псевдообратная
        x_hat, *_ = np.linalg.lstsq(A, b, rcond=None)
        x, y = x_hat.flatten().tolist()
        return x, y

    def _rmse(self, p: Tuple[float, float], pts: List[Tuple[float, float]], dists: List[float]) -> float:
        x, y = p
        errs = []
        for (xi, yi), di in zip(pts, dists):
            dd = math.hypot(x - xi, y - yi)
            errs.append((dd - di) ** 2)
        return math.sqrt(sum(errs) / len(errs))
