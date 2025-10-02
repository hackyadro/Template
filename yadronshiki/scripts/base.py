#!/usr/bin/env python3
# base.py — выбор 3 маяков по RSSI и вычисление позиции через location_by_three

import paho.mqtt.client as mqtt
import json
import math
import numpy as np
import os

BROKER = "192.168.1.104"
PORT = 1883
TOPIC = "beacons/discovered"

FILE_BEACONS = "standart.beacons"
FILE_PATH = "standart.path"
FILE_CALIBRATION = "calibration.json"

DEFAULT_TX_POWER = -59.0
DEFAULT_PATHLOSS_EXP = 2.0


def load_beacons():
    """Читает файл standart.beacons (Name;X;Y) -> dict name -> (x,y)"""
    beacons = {}
    if not os.path.exists(FILE_BEACONS):
        raise FileNotFoundError(FILE_BEACONS + " not found")
    with open(FILE_BEACONS, encoding="utf-8") as f:
        first = f.readline()
        if not first or ';' not in first or first.strip().split(';')[0].lower() != 'name':
            f.seek(0)
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(";")
            if len(parts) < 3:
                continue
            name = parts[0].strip()
            try:
                x = float(parts[1].replace(",", "."))
                y = float(parts[2].replace(",", "."))
            except ValueError:
                continue
            beacons[name] = (x, y)
    return beacons


def load_calibration():
    """Загружает calibration.json, если есть"""
    if os.path.exists(FILE_CALIBRATION):
        try:
            with open(FILE_CALIBRATION, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def rssi_to_distance(rssi, beacon_name, calibration):
    """
    Перевод RSSI->расстояние по логарифмической модели.
    Использует параметры из calibration если есть, иначе значения по умолчанию.
    """
    try:
        rssi = float(rssi)
    except Exception:
        rssi = 0.0
    if beacon_name in calibration:
        try:
            P_tx = float(calibration[beacon_name].get("P_tx", DEFAULT_TX_POWER))
            n = float(calibration[beacon_name].get("n", DEFAULT_PATHLOSS_EXP))
        except Exception:
            P_tx = DEFAULT_TX_POWER
            n = DEFAULT_PATHLOSS_EXP
    else:
        P_tx = DEFAULT_TX_POWER
        n = DEFAULT_PATHLOSS_EXP
    if n == 0:
        n = DEFAULT_PATHLOSS_EXP
    # Защита: если RSSI экстремальный, ограничим экспоненту
    try:
        d = 10 ** ((P_tx - rssi) / (10.0 * n))
    except OverflowError:
        d = float('inf')
    return d


# --- вспомогательные геометрические функции ---
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def circle_circle_intersection(c0, c1, r0, r1):
    """
    Возвращает список точек пересечения двух окружностей (0,1 или 2 точек).
    Формула стандартная.
    """
    x0, y0 = c0
    x1, y1 = c1
    dx = x1 - x0
    dy = y1 - y0
    d = math.hypot(dx, dy)
    if d == 0:
        return []  # совпадающие центры либо неразрешимая ситуация
    # нет пересечения или одна окружность внутри другой без касания
    if d > (r0 + r1) or d < abs(r0 - r1):
        return []
    # одиночная касательная точка
    a = (r0**2 - r1**2 + d**2) / (2 * d)
    # возможно небольшое отрицательное под корнем из-за погрешности — защитим
    h2 = max(0.0, r0**2 - a**2)
    xm = x0 + a * dx / d
    ym = y0 + a * dy / d
    if h2 == 0:
        return [(xm, ym)]
    h = math.sqrt(h2)
    rx = -dy * (h / d)
    ry = dx * (h / d)
    p1 = (xm + rx, ym + ry)
    p2 = (xm - rx, ym - ry)
    return [p1, p2]


def average_points(points):
    """Среднее арифметическое списка точек"""
    if not points:
        return None
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    n = len(points)
    return (sx / n, sy / n)


def weighted_centroid(centers, weights):
    """Взвешенный центр: sum(w_i * c_i) / sum(w_i)"""
    total_w = sum(weights)
    if total_w == 0:
        return None
    sx = sum(w * c[0] for c, w in zip(centers, weights))
    sy = sum(w * c[1] for c, w in zip(centers, weights))
    return (sx / total_w, sy / total_w)


# --- основная функция, интегрирующая вашу логику, но исправленная и устойчивый вариант ---
def location_by_three(c1, c2, c3, r1, r2, r3):
    """
    Оценка позиции по трем центрам и радиусам.
    Логика:
      - считаем, какие пары перекрываются;
      - если есть пересечения — используем точки пересечения (усреднение) как опорные;
      - если пересечений мало — применяем простые эвристики (взвешенные центроиды).
    Возвращает кортеж (x,y) или None.
    """
    # расстояния между центрами
    d12 = dist(c1, c2)
    d13 = dist(c1, c3)
    d23 = dist(c2, c3)

    overlap12 = d12 < (r1 + r2)
    overlap13 = d13 < (r1 + r3)
    overlap23 = d23 < (r2 + r3)

    # Соберём доступные точки пересечения (midpoints of intersection pairs)
    midpoints = []
    # Для каждой пары: если есть пересечение — возьмём среднее точек пересечения (или единственную точку)
    pts12 = circle_circle_intersection(c1, c2, r1, r2)
    if pts12:
        if len(pts12) == 1:
            midpoints.append(pts12[0])
        else:
            midpoints.append(((pts12[0][0] + pts12[1][0]) / 2.0, (pts12[0][1] + pts12[1][1]) / 2.0))

    pts13 = circle_circle_intersection(c1, c3, r1, r3)
    if pts13:
        if len(pts13) == 1:
            midpoints.append(pts13[0])
        else:
            midpoints.append(((pts13[0][0] + pts13[1][0]) / 2.0, (pts13[0][1] + pts13[1][1]) / 2.0))

    pts23 = circle_circle_intersection(c2, c3, r2, r3)
    if pts23:
        if len(pts23) == 1:
            midpoints.append(pts23[0])
        else:
            midpoints.append(((pts23[0][0] + pts23[1][0]) / 2.0, (pts23[0][1] + pts23[1][1]) / 2.0))

    # Если есть хотя бы одну midpoint (точка пересечения пар), усредняем все найденные midpoints
    if midpoints:
        avg = average_points(midpoints)
        return (round(avg[0], 6), round(avg[1], 6))

    # Если пересечений нет, но некоторые пары перекрываются — используем усреднение центроидов overlapping pairs
    overlaps = [(overlap12, (c1, c2, r1, r2, d12)),
                (overlap13, (c1, c3, r1, r3, d13)),
                (overlap23, (c2, c3, r2, r3, d23))]

    overlap_pairs = [p[1] for p in overlaps if p[0]]

    if overlap_pairs:
        # для каждой перекрывающейся пары возьмем середину между центрами, смещённую к меньшему радиусу
        pts = []
        for (ca, cb, ra, rb, dab) in overlap_pairs:
            if dab == 0:
                pts.append(((ca[0] + cb[0]) / 2.0, (ca[1] + cb[1]) / 2.0))
                continue
            # параметр t — насколько смещаемся от ca вдоль вектора к cb
            # ближе к меньшему радиусу
            t = ra / (ra + rb) if (ra + rb) != 0 else 0.5
            pts.append((ca[0] + t * (cb[0] - ca[0]), ca[1] + t * (cb[1] - ca[1])))
        avg = average_points(pts)
        return (round(avg[0], 6), round(avg[1], 6))

    # Нет пересечений и перекрытий — используем взвешенный центроид центров с весом inversely proportional to radii
    # (меньший радиус = ближе = больший вес)
    centers = [c1, c2, c3]
    # Защита от нуля
    weights = []
    for r in (r1, r2, r3):
        if r <= 0:
            weights.append(1.0)
        else:
            # инверсия и ограничение
            w = 1.0 / r
            weights.append(w)
    wc = weighted_centroid(centers, weights)
    if wc:
        return (round(wc[0], 6), round(wc[1], 6))

    return None


# --- теперь интегрируем location_by_three в поток сообщений (оставляем выбор 3 маяков по RSSI) ---
def estimate_position_3byrssi(measurements: dict, beacons: dict, calibration: dict):
    """
    Выбираем 3 маяка по RSSI (наибольший RSSI) и применяем location_by_three.
    """
    if not measurements:
        return None

    # Сортируем по RSSI по убыванию (больший RSSI = сильнее). RSSI обычно отрицательные.
    sorted_items = sorted(measurements.items(), key=lambda kv: float(kv[1]), reverse=True)
    top3 = sorted_items[:3]
    if len(top3) < 3:
        return None

    names = [t[0] for t in top3]
    rssis = [float(t[1]) for t in top3]

    # Попытка исправить регистр имени, если не найден
    for i, name in enumerate(names):
        if name not in beacons:
            found = None
            for key in beacons:
                if key.lower() == name.lower():
                    found = key
                    break
            if found:
                names[i] = found
            else:
                return None

    coords = [beacons[n] for n in names]
    # перевод RSSI->расстояние (для расчётов)
    dists = [rssi_to_distance(r, n, calibration) for r, n in zip(rssis, names)]

    # вызываем вашу функцию (исправленную)
    return location_by_three(coords[0], coords[1], coords[2], dists[0], dists[1], dists[2])


# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Подключено к брокеру")
        client.subscribe(TOPIC)
    else:
        print("Ошибка подключения:", rc)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        if "beacons" not in data:
            return
        # measurements: name->rssi
        measurements = {}
        for b in data["beacons"]:
            name = b.get("name") or b.get("addr")
            if name is None:
                continue
            try:
                rssi = float(b.get("rssi"))
            except Exception:
                continue
            measurements[name] = rssi

        pos = estimate_position_3byrssi(measurements, userdata["beacons"], userdata["calibration"])
        if pos:
            x, y = pos
            top3 = sorted(measurements.items(), key=lambda kv: kv[1], reverse=True)[:3]
            used_names = [t[0] for t in top3]
            used_rssi = [t[1] for t in top3]
            print(f"Позиция контроллера: ({x:.3f}, {y:.3f})  — использованы: {list(zip(used_names, used_rssi))}")
            with open(FILE_PATH, "a", encoding="utf-8") as f:
                f.write(f"{x:.3f};{y:.3f}\n")
        else:
            print("Не удалось оценить позицию (недостаточные/некорректные данные или геометрия плохая).")
    except Exception as e:
        print("Ошибка обработки:", e)


def main():
    beacons = load_beacons()
    calibration = load_calibration()
    client = mqtt.Client(userdata={"beacons": beacons, "calibration": calibration})
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()


if __name__ == "__main__":
    main()
