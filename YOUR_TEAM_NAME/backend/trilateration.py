# backend/trilateration.py
import math
import numpy as np
from statistics import median, stdev
from scipy.optimize import least_squares


class RobustTrilateration:
    def __init__(self, environment_factor_range=(1.5, 3.0)):
        self.env_min, self.env_max = environment_factor_range
        self.position_history = []

    def rssi_to_distance_adaptive(self, rssi_readings: list, anchor_positions: list = None) -> list:
        """Адаптивное преобразование RSSI в расстояние без калибровки"""
        if len(rssi_readings) < 3:
            distances = []
            for rssi in rssi_readings:
                n = 2.0  # среднее значение для офиса
                measured_power = -65  # типичное значение для 1 метра
                dist = 10 ** ((measured_power - rssi) / (10 * n))
                distances.append(max(0.1, dist))
            return distances

        # Используем статистику RSSI для адаптивной настройки
        rssi_median = median(rssi_readings)
        rssi_std = stdev(rssi_readings) if len(rssi_readings) > 2 else 5.0

        # Адаптивный выбор параметров
        if rssi_median > -50:
            measured_power = -45
            n = self.env_min
        elif rssi_median < -80:
            measured_power = -75
            n = self.env_max
        else:
            measured_power = -65
            n = 2.0

        # Корректировка на основе разброса сигналов
        if rssi_std > 10:
            n += 0.5

        distances = []
        for rssi in rssi_readings:
            base_dist = 10 ** ((measured_power - rssi) / (10 * n))

            if rssi > -40:
                dist = base_dist * 0.7
            elif rssi < -85:
                dist = base_dist * 1.5
            else:
                dist = base_dist

            distances.append(max(0.1, min(dist, 50.0)))

        return distances

    def estimate_environment_quality(self, rssi_readings: list) -> dict:
        """Оценка качества среды на основе статистики RSSI"""
        if len(rssi_readings) < 2:
            return {"quality": "unknown", "stability": "unknown"}

        rssi_median = median(rssi_readings)
        rssi_range = max(rssi_readings) - min(rssi_readings)

        if rssi_range < 8:
            stability = "high"
        elif rssi_range < 15:
            stability = "medium"
        else:
            stability = "low"

        if rssi_median > -55:
            quality = "excellent"
        elif rssi_median > -65:
            quality = "good"
        elif rssi_median > -75:
            quality = "fair"
        else:
            quality = "poor"

        return {
            "quality": quality,
            "stability": stability,
            "median_rssi": rssi_median,
            "range_rssi": rssi_range,
        }

    def calculate_adaptive_weights(self, rssi_readings: list, distances: list, anchor_positions: list) -> list:
        """Расчет весов на основе качества сигналов и геометрии"""
        weights = []
        env_quality = self.estimate_environment_quality(rssi_readings)

        for i, (rssi, dist) in enumerate(zip(rssi_readings, distances)):
            weight = 1.0 / (dist + 0.1)

            if rssi > -60:
                weight *= 1.5
            elif rssi < -80:
                weight *= 0.5

            if env_quality["stability"] == "high":
                weight *= 1.2
            elif env_quality["stability"] == "low":
                weight *= 0.8

            geo_factor = self._calculate_geometric_quality(i, anchor_positions)
            weight *= geo_factor

            weights.append(weight)

        total = sum(weights)
        return [w / total for w in weights] if total > 0 else [1.0 / len(weights)] * len(weights)

    def _calculate_geometric_quality(self, index: int, anchors: list) -> float:
        """Оценка геометрического качества антенны"""
        if len(anchors) < 3:
            return 1.0

        current_anchor = anchors[index]
        other_anchors = [a for i, a in enumerate(anchors) if i != index]

        vectors = []
        for anchor in other_anchors:
            dx = anchor[0] - current_anchor[0]
            dy = anchor[1] - current_anchor[1]
            vectors.append((dx, dy))

        if len(vectors) >= 2:
            angles = []
            for i in range(len(vectors)):
                for j in range(i + 1, len(vectors)):
                    dot = vectors[i][0] * vectors[j][0] + vectors[i][1] * vectors[j][1]
                    mag1 = math.sqrt(vectors[i][0] ** 2 + vectors[i][1] ** 2)
                    mag2 = math.sqrt(vectors[j][0] ** 2 + vectors[j][1] ** 2)
                    if mag1 > 0 and mag2 > 0:
                        cos_angle = dot / (mag1 * mag2)
                        cos_angle = max(-1.0, min(1.0, cos_angle))
                        angle = math.acos(cos_angle)
                        angles.append(angle)

            if angles:
                avg_angle = sum(angles) / len(angles)
                if avg_angle > 1.0:
                    return 1.2
                elif avg_angle < 0.5:
                    return 0.7

        return 1.0

    def weighted_residuals(self, params, anchors, distances, weights=None):
        """Взвешенная функция невязок"""
        x, y = params
        res = []
        for i, anchor in enumerate(anchors):
            calc_dist = math.sqrt((x - anchor[0]) ** 2 + (y - anchor[1]) ** 2)
            error = calc_dist - distances[i]
            if weights is not None:
                error *= weights[i]
            res.append(error)
        return res

    def _generate_initial_points(self, anchors, weights):
        """Генерация множественных начальных точек"""
        points = []

        wx = sum(p[0] * w for p, w in zip(anchors, weights))
        wy = sum(p[1] * w for p, w in zip(anchors, weights))
        points.append([wx, wy])

        points.append([np.median([p[0] for p in anchors]), np.median([p[1] for p in anchors])])
        points.append([np.mean([p[0] for p in anchors]), np.mean([p[1] for p in anchors])])

        return points

    def _estimate_accuracy(self, rssi_readings, env_info, optimization_cost):
        """Оценка точности позиционирования"""
        base_accuracy = 1.0

        if env_info["quality"] == "excellent":
            base_accuracy *= 0.5
        elif env_info["quality"] == "good":
            base_accuracy *= 0.8
        elif env_info["quality"] == "fair":
            base_accuracy *= 1.2
        else:
            base_accuracy *= 2.0

        if env_info["stability"] == "high":
            base_accuracy *= 0.7
        elif env_info["stability"] == "low":
            base_accuracy *= 1.5

        if optimization_cost < 0.1:
            base_accuracy *= 0.8
        elif optimization_cost > 1.0:
            base_accuracy *= 1.5

        return max(0.5, min(10.0, base_accuracy))

    def apply_smoothing(self, new_position, smoothing_factor=0.3):
        """Применяет сглаживание к позиции на основе истории"""
        if not self.position_history:
            self.position_history.append(new_position)
            return new_position

        last_position = self.position_history[-1]
        smoothed_x = last_position[0] * (1 - smoothing_factor) + new_position[0] * smoothing_factor
        smoothed_y = last_position[1] * (1 - smoothing_factor) + new_position[1] * smoothing_factor

        smoothed_position = (smoothed_x, smoothed_y)
        self.position_history.append(smoothed_position)

        if len(self.position_history) > 10:
            self.position_history.pop(0)

        return smoothed_position

    def trilaterate_improved(self, anchor_positions: list, rssi_readings: list) -> dict:
        """Улучшенная трилатерация"""
        if len(anchor_positions) < 3:
            raise ValueError("Need at least 3 anchor points")

        distances = self.rssi_to_distance_adaptive(rssi_readings, anchor_positions)
        env_info = self.estimate_environment_quality(rssi_readings)
        weights = self.calculate_adaptive_weights(rssi_readings, distances, anchor_positions)
        initial_points = self._generate_initial_points(anchor_positions, weights)

        best_solution = None
        best_cost = float("inf")

        for initial_guess in initial_points:
            try:
                result = least_squares(
                    self.weighted_residuals,
                    initial_guess,
                    args=(anchor_positions, distances, weights),
                    method="lm",
                    max_nfev=50,
                    ftol=1e-6,
                )

                if result.cost < best_cost:
                    best_cost = result.cost
                    best_solution = result
            except Exception:
                continue

        if best_solution is None:
            x = np.mean([p[0] for p in anchor_positions])
            y = np.mean([p[1] for p in anchor_positions])
            converged = False
        else:
            x, y = best_solution.x
            converged = best_solution.success

        accuracy_estimate = self._estimate_accuracy(rssi_readings, env_info, best_cost)
        smoothed_pos = self.apply_smoothing((x, y))

        return {
            "x": smoothed_pos[0],
            "y": smoothed_pos[1],
            "raw_x": x,
            "raw_y": y,
            "estimated_distances": distances,
            "environment_quality": env_info,
            "accuracy_estimate": accuracy_estimate,
            "converged": converged,
            "anchors_used": len(anchor_positions),
            "cost": best_cost if best_solution else float("inf"),
        }