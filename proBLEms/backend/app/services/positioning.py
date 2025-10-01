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
    Алгоритмы: линейная трилатерация (наименьшие квадраты) + Калман
    """

    def calculate_position(self, readings: List[Dict[str, Any]],
                           beacons: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        readings: [{'beaconId','distance'}, ...]
        beacons: [{'id','x','y'}, ...]
        Возвращает {'x','y','accuracy'}
        """
        if not readings or not beacons:
            raise ValueError("No readings or beacons")

        # карта маяков
        beacon_map = {b["id"]: b for b in beacons}

        # оставим только те ридинги, для которых есть конфиг
        usable = [r for r in readings if r["name"] in beacon_map]

        if len(usable) < 3:
            # минимум 3 маяка для 2D
            raise ValueError("At least 3 beacons required for trilateration")

        # возьмём топ-4 по близости
        usable.sort(key=lambda r: r["distance"], reverse=True)
        top = usable[:4] if len(usable) > 4 else usable

        pts = []
        dists = []
        for reading in top:
            beacon = beacon_map[reading["name"]]
            pts.append((beacon["x"], beacon["y"]))
            dists.append(reading["distance"])

        x, y = self._least_squares_trilateration(pts, dists)
        # оценка точности — rmse по разнице фактических расстояний до точек
        rmse = self._rmse((x, y), pts, dists)
        return {"x": float(x), "y": float(y), "accuracy": float(rmse)}

    def _least_squares_trilateration(
            self, pts: List[Tuple[float, float]],
            dists: List[float]) -> Tuple[float, float]:
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

    def _rmse(self, p: Tuple[float, float], pts: List[Tuple[float, float]],
              dists: List[float]) -> float:
        x, y = p
        errs = []
        for (xi, yi), di in zip(pts, dists):
            dd = math.hypot(x - xi, y - yi)
            errs.append((dd - di) ** 2)
        return math.sqrt(sum(errs) / len(errs))
