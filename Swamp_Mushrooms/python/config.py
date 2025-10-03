import threading
import pos_estimator
from pathlib import Path 
import os

def _load_beacons_from_file(relpath="../data/beacons_kpa.beacons"):
    try:
        base = Path(__file__).resolve().parent
        fpath = (base / Path(relpath)).resolve()
        if not fpath.exists():
            print(f"[WARN] beacons file not found: {fpath}")
            return None

        beacons = {}
        text = fpath.read_text(encoding="utf-8").strip()
        lines = text.splitlines()

        # пропускаем заголовок если первая строка содержит Name;X;Y
        if lines and "Name" in lines[0]:
            lines = lines[1:]

        for ln in lines:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = ln.split(";")
            if len(parts) < 3:
                print(f"[WARN] bad line: {ln}")
                continue
            name, xs, ys = parts[0], parts[1], parts[2]
            try:
                x = float(xs.replace(",", "."))
                y = float(ys.replace(",", "."))
                beacons[name] = (x, y)
            except Exception as e:
                print(f"[WARN] can't parse {ln}: {e}")

        if beacons:
            print(f"[INFO] Loaded {len(beacons)} beacons from {fpath}")
            return beacons
        else:
            return None
    except Exception as e:
        print(f"[ERROR] loading beacons file failed: {e}")
        return None


# Пробуем загрузить, иначе fallback
_BEACONS_FROM_FILE = _load_beacons_from_file("../data/beacons_kpa.beacons")
BEACONS = _BEACONS_FROM_FILE

# глобальное хранилище последних значений
LAST_VALUES = {}
RSSI_FILT = {}
ALPHA = 0.15  # коэффициент сглаживания

# параметры маяков
BEACON_PARAMS = {k: {"tx_power": -70.0, "n": 3.3} for k in BEACONS.keys()}

# параметры окна и синхронизация
WINDOW_SECONDS = 5.0
buf_lock = threading.Lock()

# EKF instance
ekf = pos_estimator.create_ekf()
