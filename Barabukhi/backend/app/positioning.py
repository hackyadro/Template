import math
import numpy as np
from typing import List, Tuple, Optional


class BeaconData:
    """Данные маяка для расчётов"""
    def __init__(self, name: str, x: float, y: float):
        self.name = name
        self.x = x
        self.y = y


class PositioningEngine:
    """
    Движок для вычисления позиции на основе RSSI измерений от BLE маяков.
    Использует трилатерацию и метод наименьших квадратов.
    """

    # Константы для вычисления расстояния по RSSI
    # Формула: distance = 10 ^ ((RSSI_AT_1M - RSSI) / (10 * PATH_LOSS_EXPONENT))
    RSSI_AT_1M = -59  # RSSI на расстоянии 1 метр (калибровочное значение)
    PATH_LOSS_EXPONENT = 2.0  # Коэффициент потерь сигнала (2.0 для свободного пространства, 2-4 для помещений)

    @staticmethod
    def rssi_to_distance(rssi: int, rssi_at_1m: int = RSSI_AT_1M, path_loss_exponent: float = PATH_LOSS_EXPONENT) -> float:
        """
        Преобразует RSSI в расстояние в метрах.

        Args:
            rssi: Измеренное значение RSSI в dBm
            rssi_at_1m: Калибровочное значение RSSI на расстоянии 1 метр
            path_loss_exponent: Коэффициент потерь сигнала

        Returns:
            Расстояние в метрах
        """
        if rssi == 0:
            return -1.0

        ratio = (rssi_at_1m - rssi) / (10.0 * path_loss_exponent)
        distance = math.pow(10, ratio)
        return round(distance, 2)

    @staticmethod
    def trilateration(beacons: List[BeaconData], distances: List[float]) -> Optional[Tuple[float, float, float]]:
        """
        Вычисляет позицию методом трилатерации.

        Args:
            beacons: Список маяков с известными координатами
            distances: Список расстояний до каждого маяка

        Returns:
            Кортеж (x, y, accuracy) или None если вычисление невозможно
        """
        if len(beacons) < 3:
            return None

        # Используем метод наименьших квадратов для решения системы уравнений
        # Формируем матрицы A и b для системы Ax = b
        n = len(beacons)
        A = np.zeros((n - 1, 2))
        b = np.zeros(n - 1)

        # Берем первый маяк как опорную точку
        x1, y1 = beacons[0].x, beacons[0].y
        r1 = distances[0]

        for i in range(1, n):
            xi, yi = beacons[i].x, beacons[i].y
            ri = distances[i]

            A[i - 1, 0] = 2 * (xi - x1)
            A[i - 1, 1] = 2 * (yi - y1)
            b[i - 1] = (r1**2 - ri**2 - x1**2 - y1**2 + xi**2 + yi**2)

        try:
            # Решаем систему методом наименьших квадратов
            position, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
            x, y = position[0], position[1]

            # Вычисляем точность на основе остатков
            if len(residuals) > 0:
                accuracy = float(np.sqrt(residuals[0] / n))
            else:
                # Если residuals пусто, вычисляем вручную
                accuracy = 0.0
                for i, beacon in enumerate(beacons):
                    calculated_dist = math.sqrt((x - beacon.x)**2 + (y - beacon.y)**2)
                    accuracy += (calculated_dist - distances[i])**2
                accuracy = math.sqrt(accuracy / n)

            return (round(float(x), 2), round(float(y), 2), round(accuracy, 2))

        except np.linalg.LinAlgError:
            return None

    @staticmethod
    def weighted_centroid(beacons: List[BeaconData], distances: List[float]) -> Optional[Tuple[float, float, float]]:
        """
        Вычисляет позицию методом взвешенного центроида.
        Используется когда маяков меньше 3 или трилатерация не работает.

        Args:
            beacons: Список маяков с известными координатами
            distances: Список расстояний до каждого маяка

        Returns:
            Кортеж (x, y, accuracy) или None если вычисление невозможно
        """
        if len(beacons) == 0:
            return None

        # Веса обратно пропорциональны расстоянию (ближе = больший вес)
        weights = [1.0 / (d + 0.1) for d in distances]  # +0.1 чтобы избежать деления на 0
        total_weight = sum(weights)

        x = sum(beacon.x * weight for beacon, weight in zip(beacons, weights)) / total_weight
        y = sum(beacon.y * weight for beacon, weight in zip(beacons, weights)) / total_weight

        # Оценка точности - средневзвешенное отклонение
        accuracy = sum(distances[i] * weights[i] for i in range(len(distances))) / total_weight

        return (round(x, 2), round(y, 2), round(accuracy, 2))

    @classmethod
    def calculate_position(
        cls,
        signals: List[Tuple[str, int]],  # [(beacon_name, rssi), ...]
        beacons_map: dict  # {beacon_name: BeaconData}
    ) -> Optional[Tuple[float, float, float, str]]:
        """
        Главный метод для вычисления позиции.

        Args:
            signals: Список сигналов [(beacon_name, rssi), ...]
            beacons_map: Словарь маяков {beacon_name: BeaconData}

        Returns:
            Кортеж (x, y, accuracy, algorithm) или None
        """
        if not signals or not beacons_map:
            return None

        # Фильтруем сигналы и вычисляем расстояния
        valid_beacons = []
        distances = []

        for beacon_name, rssi in signals:
            if beacon_name in beacons_map:
                beacon = beacons_map[beacon_name]
                distance = cls.rssi_to_distance(rssi)
                if distance > 0:
                    valid_beacons.append(beacon)
                    distances.append(distance)

        if len(valid_beacons) == 0:
            return None

        # Пробуем трилатерацию если есть 3+ маяка
        if len(valid_beacons) >= 3:
            result = cls.trilateration(valid_beacons, distances)
            if result:
                x, y, accuracy = result
                return (x, y, accuracy, "trilateration")

        # Иначе используем взвешенный центроид
        result = cls.weighted_centroid(valid_beacons, distances)
        if result:
            x, y, accuracy = result
            return (x, y, accuracy, "weighted_centroid")

        return None
