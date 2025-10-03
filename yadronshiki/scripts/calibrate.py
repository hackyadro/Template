# calibrate.py
import csv
import math
import json
from collections import defaultdict
import numpy as np

INPUT_CSV = "rssi_measurements.csv"   # columns: beacon_name,distance_m,rssi
OUTPUT_JSON = "calibration.json"

def load_measurements(path):
    data = defaultdict(list)
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0].strip().lower() == 'beacon_name':  # только шапку пропускаем
                continue
            name = row[0].strip()
            try:
                d = float(row[1].replace(',', '.'))
                rssi = float(row[2].replace(',', '.'))
            except Exception:
                continue
            if d <= 0:
                continue
            data[name].append((d, rssi))
    return data


def fit_tx_n(pairs):
    xs = np.array([math.log10(d) for d, _ in pairs])
    ys = np.array([rssi for _, rssi in pairs])
    if len(xs) < 2:
        return None
    b, a = np.polyfit(xs, ys, 1)
    P_tx = float(a)
    n = float(-b / 10.0)
    y_pred = a + b * xs
    residuals = ys - y_pred
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((ys - np.mean(ys))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0.0
    return {"P_tx": P_tx, "n": n, "r2": float(r2), "samples": len(pairs)}

def main():
    data = load_measurements(INPUT_CSV)
    result = {}
    for beacon, pairs in data.items():
        if len(pairs) < 2:
            print(f"[ERROR] слишком мало данных для {beacon}: {len(pairs)} (нужно хотя бы 2)")
            continue
        elif len(pairs) < 5:
            print(f"[WARN] мало данных для {beacon}: {len(pairs)} (лучше >=20)")
        cal = fit_tx_n(pairs)
        if cal:
            result[beacon] = cal
            print(f"{beacon}: P_tx={cal['P_tx']:.2f} dBm, n={cal['n']:.3f}, "
                  f"r2={cal['r2']:.3f}, samples={cal['samples']}")
    if not result:
        print("[ERROR] нет данных для сохранения, calibration.json не будет обновлён")
        return
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Калибровка сохранена в", OUTPUT_JSON)

if __name__ == "__main__":
    main()
