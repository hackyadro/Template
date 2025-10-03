import math
from typing import List, Dict, Any, Tuple
import numpy as np


class Kalman1D:
    """Простой 1D Калман для сглаживания"""
    def __init__(self, q: float = 0.1, r: float = 0.5):
        self.x = 0.0
        self.P = 1.0
        self.Q = q  # шум процесса
        self.R = r  # шум измерения
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
    def __init__(self, q: float = 0.01, r: float = 1):
        self.fx = Kalman1D(q, r)
        self.fy = Kalman1D(q, r)

    def update(self, x: float, y: float) -> Tuple[float, float]:
        return self.fx.update(x), self.fy.update(y)


class PositioningService:
    """
    Взвешенная нелинейная трилатерация (Гаусс–Ньютон) + оценка RMSE.
    """

    def __init__(self):
        self.kalman = Kalman2D(q=0.003, r=2)

    def calculate_position(self, readings: List[Dict[str, Any]],
                           beacons: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        readings: [{'beaconId','distance'}, ...]
        beacons:  [{'id','x','y'}, ...]
        Возвращает {'x','y','accuracy'}
        """
        if not readings or not beacons:
            raise ValueError("No readings or beacons")

        # карта маяков
        beacon_map = {str(b["id"]): b for b in beacons}

        # нормализуем ключи измерений (поддержим и старое 'name' на всякий случай)
        usable = [r for r in readings if r["name"] in beacon_map and r[
            "distance"] <= 20.0]

        # минимально 3
        if len(usable) < 3:
            raise ValueError("At least 3 beacons required for trilateration")

        # сортируем по ближним (НЕ reverse)
        usable.sort(key=lambda r: r["distance"])

        # берём до 6 ближайших (обычно 4 достаточно)
        top = usable[:]

        pts: List[Tuple[float, float]] = []
        dists: List[float] = []
        for reading in top:
            beacon = beacon_map[reading["name"]]
            pts.append((float(beacon["x"]), float(beacon["y"])))
            dists.append(float(reading["distance"]))

        # Гаусс–Ньютон c весами (веса ~ 1/d^2)
        x, y = self._gauss_newton_wls(np.array(pts), np.array(dists))

        # RMSE по невязкам
        pred = np.sqrt(
            (np.array(pts)[:, 0] - x) ** 2 + (np.array(pts)[:, 1] - y) ** 2)
        rmse = float(np.sqrt(np.mean((pred - dists) ** 2)))
        return {"x": float(x), "y": float(y), "accuracy": float(rmse)}

    def _gauss_newton_wls(self, pts: np.ndarray, dists: np.ndarray,
                          iters: int = 30) -> Tuple[float, float]:
        """
        Нелинейный WLS:
          минимизируем sum(w_i * (||p - P_i|| - d_i)^2),
          w_i = 1 / max(d_i, eps)^2.
        """
        eps = 1e-3
        # начальная оценка — взв. среднее якорей по 1/d^2
        w0 = 1.0 / np.maximum(dists, eps) ** 2
        x = np.average(pts[:, 0], weights=w0)
        y = np.average(pts[:, 1], weights=w0)

        for _ in range(iters):
            dx = x - pts[:, 0]
            dy = y - pts[:, 1]
            ri = np.sqrt(dx * dx + dy * dy)  # текущие расстояния
            # защищаемся от нуля
            ri_safe = np.maximum(ri, eps)

            # невязки
            r = ri - dists

            # Якобиан (dr/dx, dr/dy) для каждого i
            J = np.stack([dx / ri_safe, dy / ri_safe], axis=1) # nx2

            # веса
            W = np.diag(1.0 / np.maximum(dists, eps) ** 2) # nxn

            # шаг ГН: (J^T W J) Δ = - J^T W r
            JT_W = J.T @ W # 2xn
            H = JT_W @ J # 2x2
            g = JT_W @ r # 2x1

            # регуляризация на случай плохой геометрии
            lam = 1e-3
            H_reg = H + lam * np.eye(2) # 2x2

            try:
                delta = -np.linalg.solve(H_reg, g)
            except np.linalg.LinAlgError:
                break

            # апдейт
            x += float(delta[0])
            y += float(delta[1])

            # критерий сходимости
            if np.linalg.norm(delta) < 1e-4:
                break

        return x, y
