from typing import List, Dict, Any, Tuple
import math
import numpy as np


class Kalman1D:
    """Простой 1D Калман для сглаживания"""
    def __init__(self, q: float = 0.02, r: float = 0.10):
        self.x = 0.0
        self.P = 1.0
        self.Q = q  # шум процесса
        self.R = r  # шум измерения
        self.initialized = False

    def update(self, measurement: float) -> float:
        if not self.initialized:
            self.x = measurement
            self.initialized = True
            return self.x

        # predict
        self.P = self.P + self.Q
        # update
        K = self.P / (self.P + self.R)
        self.x = self.x + K * (measurement - self.x)
        self.P = (1.0 - K) * self.P
        return self.x


class Kalman2D:
    def __init__(self, q: float = 0.02, r: float = 0.10):
        self.fx = Kalman1D(q, r)
        self.fy = Kalman1D(q, r)

    def update(self, x: float, y: float) -> Tuple[float, float]:
        return self.fx.update(x), self.fy.update(y)

    def reset(self):
        self.fx = Kalman1D(self.fx.Q, self.fx.R)
        self.fy = Kalman1D(self.fy.Q, self.fy.R)


def _angle(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    """Угол ABC (в радианах) — помогает отсекать «плоские» треугольники."""
    ax, ay = a
    bx, by = b
    cx, cy = c
    v1 = np.array([ax - bx, ay - by], dtype=float)
    v2 = np.array([cx - bx, cy - by], dtype=float)
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    cosang = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(math.acos(cosang))


class PositioningService:
    """
    Линейная трилатерация (МНК, взвешенная) + Калман.
    Пытаемся выбрать геометрически «здоровый» поднабор маяков.
    """

    def __init__(self):
        self.kalman = Kalman2D(q=0.02, r=0.10)

    def reset_kalman(self):
        self.kalman.reset()

    def calculate_position(self, readings: List[Dict[str, Any]],
                           beacons: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        readings: [{'beaconId','distance'}, ...]
        beacons:  [{'id','x','y'}, ...]
        Возвращает {'x','y','accuracy'}
        """
        if not readings or not beacons:
            return {"x": 0.0, "y": 0.0, "accuracy": 2.0}

        # карта маяков
        beacon_map = {b["id"]: b for b in beacons}

        # корректный ключ: beaconId
        usable = [r for r in readings if r.get("beaconId") in beacon_map and "distance" in r]
        if len(usable) < 3:
            # взвешенный центроид по тому, что есть
            return self._centroid_fallback(usable, beacon_map)

        # сортируем по возрастанию дистанции — ближние важнее и стабильнее
        usable.sort(key=lambda r: r["distance"])

        # возьмём 3–4 ближайших (обычно 4 лучше, но иногда 3 даёт более «жёсткую» геометрию)
        top = usable[:4]

        pts: List[Tuple[float, float]] = []
        dists: List[float] = []
        for r in top:
            b = beacon_map[r["beaconId"]]
            pts.append((float(b["x"]), float(b["y"])))
            dists.append(float(r["distance"]))

        # Попробуем отбросить плохую геометрию: если 4 маяка дают «плоский» набор,
        # перейдём на лучшую тройку по качеству углов
        pts_sel, dists_sel = self._choose_well_spread(pts, dists)

        try:
            x, y = self._weighted_least_squares_trilateration(pts_sel, dists_sel)
        except np.linalg.LinAlgError:
            x, y = self._weighted_centroid(pts_sel, dists_sel)

        # сглаживание
        xs, ys = self.kalman.update(x, y)

        # оценка точности как RMSE по выбранным точкам
        rmse = self._rmse((xs, ys), pts_sel, dists_sel)
        return {"x": float(xs), "y": float(ys), "accuracy": float(rmse)}

    # ---------- математика ----------

    def _choose_well_spread(self, pts: List[Tuple[float, float]],
                             dists: List[float]) -> Tuple[List[Tuple[float, float]], List[float]]:
        """
        Выбираем 3–4 точки с «здоровыми» углами, избегаем почти коллинеарных троек.
        Если 4 — ок, иначе подбираем «лучшую» тройку по сумме углов ближе к 180°.
        """
        if len(pts) <= 3:
            return pts, dists

        # Проверим «плоскость» набора из 4: возьмём любые три, посчитаем углы
        # Если углы плохие (очень маленький или очень большой, ~0° или ~180°), уменьшим до 3.
        from itertools import combinations
        best_combo = None
        best_score = -1.0

        for idxs in combinations(range(len(pts)), 3):
            a, b, c = pts[idxs[0]], pts[idxs[1]], pts[idxs[2]]
            # сумма углов треугольника = π, но «качество» — равномерность углов
            angA = _angle(b, a, c)
            angB = _angle(a, b, c)
            angC = _angle(a, c, b)
            min_ang = min(angA, angB, angC)
            # хотим избегать очень острых углов: максимизируем минимальный угол
            score = min_ang
            if score > best_score:
                best_score = score
                best_combo = idxs

        if best_combo is None:
            return pts[:3], dists[:3]

        sel_pts = [pts[i] for i in best_combo]
        sel_d   = [dists[i] for i in best_combo]
        return sel_pts, sel_d

    def _weighted_least_squares_trilateration(
            self, pts: List[Tuple[float, float]], dists: List[float]) -> Tuple[float, float]:
        """
        Линеаризация «относительно опорного маяка» + ВЗВЕШЕННАЯ МНК (веса ~ 1/d^2).
        ВАЖНО: решение даёт абсолютные x,y — ничего «добавлять» к опорной точке не нужно.
        """
        if len(pts) < 3:
            raise ValueError("Need >= 3 points")

        # опорный — ближайший (минимум влияния ошибки)
        ref = int(np.argmin(dists))
        x1, y1 = pts[ref]
        d1 = dists[ref]

        A = []
        b = []
        w = []

        eps = 1e-6
        for i, ((xi, yi), di) in enumerate(zip(pts, dists)):
            if i == ref:
                continue
            A.append([2.0 * (xi - x1), 2.0 * (yi - y1)])
            b.append(di**2 - d1**2 - xi**2 + x1**2 - yi**2 + y1**2)
            w.append(1.0 / max(di, eps) ** 2)  # ближние — тяжелее

        A = np.asarray(A, dtype=float)
        b = np.asarray(b, dtype=float).reshape(-1, 1)
        W = np.diag(w)

        # решаем (A^T W A) x = A^T W b
        ATA = A.T @ W @ A
        ATb = A.T @ W @ b
        x_hat = np.linalg.solve(ATA, ATb)  # если синг., выкинет LinAlgError
        x, y = x_hat.flatten().tolist()
        return x, y  # уже абсолютные координаты

    def _weighted_centroid(self, pts: List[Tuple[float, float]],
                           dists: List[float]) -> Tuple[float, float]:
        weights = []
        eps = 0.1  # чтобы не делить на ноль
        for d in dists:
            # 1/d^2 — агрессивнее тянет к близким
            weights.append(1.0 / (max(d, eps) ** 2))
        W = sum(weights)
        x = sum(px * w for (px, _), w in zip(pts, weights)) / W
        y = sum(py * w for (_, py), w in zip(pts, weights)) / W
        return x, y

    def _centroid_fallback(self, readings: List[Dict[str, Any]],
                           beacon_map: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        if not readings:
            return {"x": 0.0, "y": 0.0, "accuracy": 2.0}
        pts = [(float(beacon_map[r["beaconId"]]["x"]),
                float(beacon_map[r["beaconId"]]["y"])) for r in readings]
        dists = [float(r["distance"]) for r in readings]
        x, y = self._weighted_centroid(pts, dists)
        # грубая оценка «точности» без трилатерации
        return {"x": float(x), "y": float(y), "accuracy": 1.0}

    def _rmse(self, p: Tuple[float, float], pts: List[Tuple[float, float]],
              dists: List[float]) -> float:
        x, y = p
        errs = []
        for (xi, yi), di in zip(pts, dists):
            dd = math.hypot(x - xi, y - yi)
            errs.append((dd - di) ** 2)
        return math.sqrt(sum(errs) / len(errs)) if errs else 1.0
