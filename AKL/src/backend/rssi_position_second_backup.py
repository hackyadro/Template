from dataclasses import dataclass
import os
import json
import math
import csv

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
STATIONS_PATH = os.path.join(CUR_DIR, "data", "beacons.txt")


@dataclass
class Position:
    x: float
    y: float


@dataclass
class StationRssi:
    name: str
    rssi: int


def check_stations_path() -> bool:
    return os.path.exists(STATIONS_PATH)


def load_stations() -> dict[str, Position]:
    stations: dict[str, Position] = {}
    with open(STATIONS_PATH, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        for row in reader:
            stations[row["Name"]] = Position(float(row["X"]), float(row["Y"]))
    return stations


# def rssi_to_distance(rssi: float, tx_power: float = -59.0, n: float = 2.0) -> float:
#     return 10 ** ((tx_power - rssi) / (10 * n))

d0 = 1.0
rssi_d0 = -40
n = 2.75

def rssi_to_distance(rssi: float) -> float:
    """Переводит RSSI (дБм) в расстояние (м)"""
    return d0 * 10 ** ((rssi_d0 - rssi) / (10 * n))

def get_board_pos(data: list[StationRssi]) -> Position:
    if len(data) < 3:
        return
    
    stations_pos = load_stations()
    data_sorted = sorted(data, key=lambda s: s.rssi, reverse=True)

    s1, s2, s3 = data_sorted[:3]
    c1, c2, c3 = stations_pos[s1.name], stations_pos[s2.name], stations_pos[s3.name]

    print(f"ОПОРНЫЙ - {s1.name}")
    r1 = rssi_to_distance(s1.rssi)
    d2 = rssi_to_distance(s2.rssi)
    d3 = rssi_to_distance(s3.rssi)

    def unit_vector(a: Position, b: Position):
        dx, dy = b.x - a.x, b.y - a.y
        l = math.hypot(dx, dy)
        return (dx/l, dy/l) if l != 0 else (1, 0)

    def point_on_circle(center: Position, radius: float, toward: Position, invert=False) -> Position:
        ux, uy = unit_vector(center, toward)
        if invert:  # берем противоположную сторону окружности
            ux, uy = -ux, -uy
        return Position(center.x + ux*radius, center.y + uy*radius)

    def pull_error(p: Position, beacon: Position, dist: float) -> float:
        actual = math.hypot(p.x - beacon.x, p.y - beacon.y)
        return abs(actual - dist)

    # Кандидаты: нормальные и инвертированные
    candidates = []
    for inv2 in (False, True):
        for inv3 in (False, True):
            p2 = point_on_circle(c1, r1, c2, invert=inv2)
            p3 = point_on_circle(c1, r1, c3, invert=inv3)

            e2 = pull_error(p2, c2, d2)
            e3 = pull_error(p3, c3, d3)

            # средневзвешенная точка
            w2 = 1 / (e2 + 1e-3)
            w3 = 1 / (e3 + 1e-3)
            vx = (p2.x * w2 + p3.x * w3) / (w2 + w3)
            vy = (p2.y * w2 + p3.y * w3) / (w2 + w3)

            dx, dy = vx - c1.x, vy - c1.y
            l = math.hypot(dx, dy)
            if l == 0:
                pos = p2
            else:
                pos = Position(c1.x + dx/l*r1, c1.y + dy/l*r1)

            total_error = pull_error(pos, c2, d2) + pull_error(pos, c3, d3)
            candidates.append((total_error, pos))

    # Выбираем кандидата с минимальной суммарной ошибкой
    best_err, best_pos = min(candidates, key=lambda x: x[0])
    return best_pos
