"""
Оптимизированный алгоритм позиционирования с:
- Калибровкой alpha/beta по известной точке
- Робастной оценкой (Huber)
- Нелинейным МНК (Levenberg-Marquardt) с якорем к предыдущей позиции
- Взвешиванием по количеству проб и геометрии
"""

import math
from typing import Dict, Tuple, Optional
import numpy as np


class AdvancedPositioningEngine:
    """Продвинутый движок позиционирования с калибровкой и робастной оценкой"""

    # Калибровочные данные для базовой точки
    # MAC -> {'name': beacon_name, 'rssi': среднее_значение}
    CALIBRATION_MEASUREMENTS = {
        '88:57:21:23:34:CA': {'name': 'beacon_1', 'rssi': -63.3},
        '84:1F:E8:09:88:96': {'name': 'beacon_2', 'rssi': -57.9},
        '84:1F:E8:45:49:8E': {'name': 'beacon_3', 'rssi': -66.8},
        '88:57:21:23:3D:D6': {'name': 'beacon_4', 'rssi': -76.2},
        '88:57:21:23:50:46': {'name': 'beacon_5', 'rssi': -76.8},
        '88:57:21:23:3F:6E': {'name': 'beacon_6', 'rssi': -78.0},
        '4C:C3:82:C4:27:AA': {'name': 'beacon_7', 'rssi': -93.5},
    }

    def __init__(self, base_point: Tuple[float, float] = (0.0, 0.0)):
        """
        Инициализация движка позиционирования.

        Args:
            base_point: Базовая калибровочная точка (base_x, base_y) из БД
        """
        self.alpha = -59.0  # RSSI на 1м (будет калиброваться)
        self.beta = 2.0     # Path loss exponent (будет калиброваться)
        self.prev_position: Optional[Tuple[float, float]] = None
        self.known_calibration_point = base_point

    @staticmethod
    def rssi_to_distance(rssi: float, alpha: float, beta: float) -> float:
        """
        Конвертация RSSI в расстояние.

        Формула: d = 10^((alpha - rssi) / (10*beta))

        Args:
            rssi: Уровень сигнала в дБм
            alpha: RSSI на 1 метре
            beta: Path loss exponent

        Returns:
            Расстояние в метрах
        """
        return 10.0 ** ((alpha - rssi) / (10.0 * beta))

    @staticmethod
    def calibrate_alpha_beta(
        beacons: Dict[str, Tuple[float, float]],
        measurements: Dict[str, Dict[str, float]],
        known_position: Tuple[float, float],
        initial_beta: float = 2.0
    ) -> Tuple[float, float]:
        """
        Калибровка параметров распространения сигнала по известной точке.
        Использует робастную оценку (Huber) для устойчивости к выбросам.

        Args:
            beacons: {beacon_name: (x, y)} - координаты маяков
            measurements: {mac: {'name': name, 'rssi': value}} - измерения RSSI
            known_position: (x, y) - известная позиция для калибровки
            initial_beta: Начальное значение beta

        Returns:
            (alpha, beta) - калиброванные параметры
        """
        x0, y0 = known_position
        xs, ys = [], []

        # Собираем данные для регрессии
        for info in measurements.values():
            name = info['name']
            if name not in beacons:
                continue
            rssi = float(info['rssi'])
            bx, by = beacons[name]
            d = math.hypot(x0 - bx, y0 - by)
            if d <= 0:
                continue
            xs.append(math.log10(d))
            ys.append(rssi)

        if len(xs) < 2:
            return (-59.0, initial_beta)

        # Линейная регрессия: rssi = alpha + m*log10(d), где m = -10*beta
        X = np.vstack([np.ones(len(xs)), np.array(xs)]).T
        Y = np.array(ys, dtype=float)
        theta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        alpha, m = float(theta[0]), float(theta[1])
        beta = max(0.5, min(6.0, -m / 10.0))

        # Робастная дооценка (Huber, 1 итерация)
        resid = Y - (alpha + m * np.array(xs))
        mad = float(np.median(np.abs(resid - np.median(resid)))) or 1.0
        c = 1.345 * mad
        w = [(1.0 if abs(r) <= c else c/abs(r)) for r in resid]
        W = np.diag(w)
        theta2, *_ = np.linalg.lstsq(W @ X, W @ Y, rcond=None)
        alpha2, m2 = float(theta2[0]), float(theta2[1])
        beta2 = max(0.5, min(6.0, -m2 / 10.0))

        return alpha2, beta2

    @staticmethod
    def solve_position_nlls(
        beacons_xy: Dict[str, Tuple[float, float]],
        distances_by_name: Dict[str, float],
        weights_by_name: Dict[str, float],
        start_xy: Tuple[float, float],
        prior_xy: Tuple[float, float],
        prior_weight: float = 0.1,
        iters: int = 30,
        lm_lambda: float = 1e-3
    ) -> Tuple[float, float]:
        """
        Нелинейная МНК (Levenberg-Marquardt) с якорем к предыдущей позиции.

        Args:
            beacons_xy: {beacon_name: (x, y)} - координаты маяков
            distances_by_name: {beacon_name: distance} - измеренные расстояния
            weights_by_name: {beacon_name: weight} - веса измерений
            start_xy: Начальная позиция для итераций
            prior_xy: Якорная позиция (предыдущая)
            prior_weight: Сила якоря (regularization)
            iters: Максимум итераций
            lm_lambda: Параметр Levenberg-Marquardt

        Returns:
            (x, y) - вычисленная позиция
        """
        x, y = start_xy
        names = [n for n in beacons_xy if n in distances_by_name]

        if len(names) < 3:
            raise ValueError("Меньше 3 маяков для трилатерации")

        # Медиана дистанций для геометрического веса
        dvals = [distances_by_name[n] for n in names]
        med_d = float(np.median(dvals)) or 1.0

        for _ in range(iters):
            H_rows, r_vec, w_vec = [], [], []

            # Измерительные уравнения: r_i = ||p - b_i|| - d_i
            for n in names:
                xi, yi = beacons_xy[n]
                di = float(distances_by_name[n])
                dx, dy = (x - xi), (y - yi)
                r_est = math.hypot(dx, dy) + 1e-9
                resid = r_est - di

                # Градиент по (x, y)
                H_rows.append([dx / r_est, dy / r_est])
                r_vec.append(resid)

                # Веса: по samples и по геометрии
                w_samples = float(weights_by_name.get(n, 1.0))
                w_geo = 1.0 / (1.0 + (di / med_d) ** 2)
                w_vec.append(w_samples * w_geo)

            # Якорь (Tikhonov regularization) — тянем к prior_xy
            if prior_weight > 0.0:
                px, py = prior_xy
                H_rows.append([math.sqrt(prior_weight), 0.0])
                r_vec.append((x - px) * math.sqrt(prior_weight))
                w_vec.append(1.0)

                H_rows.append([0.0, math.sqrt(prior_weight)])
                r_vec.append((y - py) * math.sqrt(prior_weight))
                w_vec.append(1.0)

            H = np.array(H_rows, dtype=float)
            r = np.array(r_vec, dtype=float)
            W = np.diag(w_vec)

            # Шаг LM: (H^T W H + λ I) Δ = - H^T W r
            A = H.T @ W @ H + lm_lambda * np.eye(2)
            g = H.T @ W @ r

            try:
                delta = np.linalg.solve(A, -g)
            except np.linalg.LinAlgError:
                break

            x_new, y_new = x + float(delta[0]), y + float(delta[1])

            # Проверка сходимости
            if math.hypot(x_new - x, y_new - y) < 1e-5:
                x, y = x_new, y_new
                break

            x, y = x_new, y_new

        return x, y

    def calibrate(self, beacons: Dict[str, Tuple[float, float]], beta_fixed: Optional[float] = None):
        """
        Выполнить калибровку alpha/beta по калибровочным данным.

        Args:
            beacons: {beacon_name: (x, y)} - координаты маяков
            beta_fixed: Если задано, фиксировать beta этим значением
        """
        if beta_fixed is not None:
            # Оценить только alpha при фиксированном beta
            self.beta = float(beta_fixed)
            vals = []
            for info in self.CALIBRATION_MEASUREMENTS.values():
                name = info['name']
                if name not in beacons:
                    continue
                rssi = float(info['rssi'])
                bx, by = beacons[name]
                d = math.hypot(
                    self.known_calibration_point[0] - bx,
                    self.known_calibration_point[1] - by
                )
                if d > 0:
                    vals.append(rssi + 10.0 * self.beta * math.log10(d))
            self.alpha = float(np.mean(vals)) if vals else -59.0
        else:
            # Оценить и alpha, и beta
            self.alpha, self.beta = self.calibrate_alpha_beta(
                beacons,
                self.CALIBRATION_MEASUREMENTS,
                self.known_calibration_point,
                initial_beta=2.0
            )

    def calculate_position_with_samples(
        self,
        report_data: Dict[str, Dict[str, float]],
        beacons_map: Dict[str, Tuple[float, float]],
        rssi_threshold: float = -100.0,
        min_distance: float = 0.5,
        max_distance: float = 100.0,
        prior_weight: float = 0.1
    ) -> Optional[Tuple[float, float, float, str]]:
        """
        Вычислить позицию по отчёту с учётом количества измерений (samples).

        Args:
            report_data: {beacon_name: {'rssi': value, 'samples': count}}
            beacons_map: {beacon_name: (x, y)} - координаты маяков
            rssi_threshold: Минимальный RSSI для учёта
            min_distance: Минимальная дистанция (метры)
            max_distance: Максимальная дистанция (метры)
            prior_weight: Сила якоря к предыдущей позиции

        Returns:
            (x, y, accuracy, algorithm) или None
        """
        distances: Dict[str, float] = {}
        weights: Dict[str, float] = {}

        # Конвертируем RSSI -> дистанции с весами
        for beacon_name, info in report_data.items():
            rssi = float(info.get('rssi', -999))
            samples = int(info.get('samples', 1))

            if rssi < rssi_threshold:
                continue
            if beacon_name not in beacons_map:
                continue

            # RSSI -> расстояние
            d = self.rssi_to_distance(rssi, self.alpha, self.beta)
            d = max(min_distance, min(max_distance, d))
            distances[beacon_name] = d

            # Вес: по количеству проб + геометрический вес
            w_samp = 1.0 + 0.25 * max(0, samples - 1)
            w_geo = 1.0 / max(0.5, d) ** 2
            weights[beacon_name] = w_samp * w_geo

        if len(distances) < 3:
            return None

        # Определяем стартовую позицию
        if self.prev_position:
            start_xy = self.prev_position
            prior_xy = self.prev_position
        else:
            start_xy = self.known_calibration_point
            prior_xy = self.known_calibration_point

        try:
            # Решаем задачу позиционирования
            x, y = self.solve_position_nlls(
                beacons_map,
                distances,
                weights,
                start_xy=start_xy,
                prior_xy=prior_xy,
                prior_weight=prior_weight,
                iters=30,
                lm_lambda=1e-3
            )

            # Обновляем предыдущую позицию для следующей итерации
            self.prev_position = (x, y)

            # Вычисляем accuracy как среднюю ошибку
            errors = []
            for name, d_measured in distances.items():
                bx, by = beacons_map[name]
                d_calc = math.hypot(x - bx, y - by)
                errors.append(abs(d_calc - d_measured))

            accuracy = sum(errors) / len(errors) if errors else 0.0

            return x, y, accuracy, "nlls_lm_with_samples"

        except Exception:
            return None
