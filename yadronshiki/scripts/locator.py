#!/usr/bin/env python3
# base.py — выбор 3 маяков по RSSI и вычисление позиции через location_by_three

import paho.mqtt.client as mqtt
import json
import math
import numpy as np
import os

BROKER = "mqtt"
PORT = 1883
TOPIC = "beacons/discovered"

FILE_BEACONS = "/app/standart.beacons"
FILE_PATH = "/app/standart.path"
FILE_CALIBRATION = "/app/calibration.json"

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

def location_by_three(c1, c2, c3, r1, r2, r3):
    """
    Оценка позиции по трём центрам c1,c2,c3 и радиусам r1,r2,r3.
    Использует простые геометрические эвристики:
      - если есть пересечения пар кругов — берём средние точки пересечений и усредняем;
      - если пересечений нет, но есть перекрытия пар — берём смещённые точки вдоль векторов центров;
      - если вообще нет перекрытий — используем взвешенный по 1/r центроид.
    Возвращает [x, y] или None.
    """
    # расстояния между центрами
    d12 = dist(c1, c2)
    d13 = dist(c1, c3)
    d23 = dist(c2, c3)

    overlap12 = d12 < (r1 + r2)
    overlap13 = d13 < (r1 + r3)
    overlap23 = d23 < (r2 + r3)

    count = int(overlap12) + int(overlap13) + int(overlap23)

    def unit_vec(a, b):
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        mag = hypot(dx, dy)
        if mag == 0:
            return (0.0, 0.0)
        return (dx / mag, dy / mag)

    def avg_point(pts):
        if not pts:
            return None
        sx = sum(p[0] for p in pts)
        sy = sum(p[1] for p in pts)
        n = len(pts)
        return (sx / n, sy / n)

    # helper: средняя точка пересечения двух окружностей (усреднение двух пересечений)
    def mid_of_circle_intersection(a, b, ra, rb):
        from math import sqrt
        x0, y0 = a
        x1, y1 = b
        dx = x1 - x0
        dy = y1 - y0
        d = hypot(dx, dy)
        if d == 0:
            return None
        # проверяем наличие пересечения
        if d > (ra + rb) or d < abs(ra - rb):
            return None
        # расстояние от a до линии, проходящей через точки пересечения
        a_len = (ra * ra - rb * rb + d * d) / (2 * d)
        h2 = max(0.0, ra * ra - a_len * a_len)
        xm = x0 + a_len * dx / d
        ym = y0 + a_len * dy / d
        if h2 == 0:
            return (xm, ym)
        h = sqrt(h2)
        rx = -dy * (h / d)
        ry = dx * (h / d)
        p1 = (xm + rx, ym + ry)
        p2 = (xm - rx, ym - ry)
        # возвращаем усреднённую точку пересечения
        return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)

    # 1) если все три пары перекрываются — используем точки, смещённые от центров (по радиусу) и усреднение
    if count == 3:
        u12 = unit_vec(c1, c2)
        u13 = unit_vec(c1, c3)
        u23 = unit_vec(c2, c3)
        c12 = (c1[0] + r1 * u12[0], c1[1] + r1 * u12[1])
        c13 = (c1[0] + r1 * u13[0], c1[1] + r1 * u13[1])
        c32 = (c2[0] + r2 * u23[0], c2[1] + r2 * u23[1])
        to13 = (c13[0] - c12[0], c13[1] - c12[1])
        to32 = (c32[0] - c12[0], c32[1] - c12[1])
        centrevec = (2.0 / 3.0 * (to13[0] + to32[0]), 2.0 / 3.0 * (to13[1] + to32[1]))
        return [round(centrevec[0] + c12[0], 6), round(centrevec[1] + c12[1], 6)]

    # 2) если есть хотя бы одна пара пересечения (точки пересечения), усредняем найденные midpoints
    midpoints = []
    m12 = mid_of_circle_intersection(c1, c2, r1, r2)
    if m12:
        midpoints.append(m12)
    m13 = mid_of_circle_intersection(c1, c3, r1, r3)
    if m13:
        midpoints.append(m13)
    m23 = mid_of_circle_intersection(c2, c3, r2, r3)
    if m23:
        midpoints.append(m23)
    if midpoints:
        p = avg_point(midpoints)
        return [round(p[0], 6), round(p[1], 6)]

    # 3) если нет пересечений, но есть пары, которые перекрываются (count == 1 or 2)
    if count in (1, 2):
        pts = []
        pairs = [
            (c1, c2, r1, r2, d12),
            (c1, c3, r1, r3, d13),
            (c2, c3, r2, r3, d23),
        ]
        for (ca, cb, ra, rb, dab) in pairs:
            if dab < (ra + rb):
                # точка вдоль вектора от ca к cb, смещённая пропорционально радиусам
                if ra + rb == 0:
                    t = 0.5
                else:
                    t = ra / (ra + rb)
                pts.append((ca[0] + t * (cb[0] - ca[0]), ca[1] + t * (cb[1] - ca[1])))
        if pts:
            p = avg_point(pts)
            return [round(p[0], 6), round(p[1], 6)]
        # если count == 2, но по какой-то причине pts пуст — падём к следующему блоку

    # 4) нет пересечений и нет перекрытий — используем взвешенный центроид центров (вес ~ 1/r)
    centers = [c1, c2, c3]
    radii = [r1, r2, r3]
    weights = []
    for r in radii:
        if r <= 0 or not (r == r):  # защита от нуля/NaN
            weights.append(1.0)
        else:
            weights.append(1.0 / r)
    wsum = sum(weights)
    if wsum == 0:
        return None
    cx = sum(w * c[0] for w, c in zip(weights, centers)) / wsum
    cy = sum(w * c[1] for w, c in zip(weights, centers)) / wsum
    return [round(cx, 6), round(cy, 6)]

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
