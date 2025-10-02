#!/usr/bin/env python3
# live_beacon_distance.py
# Пример: python3 live_beacon_distance.py --beacon beacon5 --interval 0.1 --window 60

from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import pandas as pd

# ---------- utils ----------
def norm_name(s: str) -> str:
    if s is None: return ""
    return re.sub(r"[\s:\-_/]+", "", str(s).strip().lower())

def decode_csv_json_field(s: str) -> str:
    if s is None: return ""
    s = s.strip()
    if len(s) >= 2 and (s[0] == s[-1] == '"' or s[0] == s[-1] == "'"):
        s = s[1:-1]
    s = s.replace('""', '"').replace('\\"', '"')
    return s

def read_last_records(csv_path: Path, max_lines: int) -> list[dict]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []
    try:
        df = pd.read_csv(csv_path, sep=",", dtype=str, on_bad_lines="skip")
        if df.empty: return []
        cols = [c for c in ["ts","beacons_json"] if c in df.columns]
        if not cols: return []
        tail = df[cols].tail(max_lines)
        return [{"ts": r.get("ts",""), "beacons_json": r.get("beacons_json","")} for _, r in tail.iterrows()]
    except Exception:
        return []

def rssi_list_for_beacon(records: list[dict], beacon_key: str) -> list[float]:
    vals: List[float] = []
    for r in records:
        try:
            arr = json.loads(decode_csv_json_field(r["beacons_json"]))
        except Exception:
            continue
        if not isinstance(arr, list): continue
        for it in arr:
            name = it.get("name") or it.get("id") or it.get("beacon") or it.get("mac")
            rssi = it.get("rssi")
            if name is None or rssi is None: continue
            if norm_name(name) == beacon_key:
                vals.append(float(rssi))
    return vals

def try_load_txpower(beacons_path: Path, beacon_key: str) -> float | None:
    if not beacons_path.exists(): return None
    try:
        df = pd.read_csv(beacons_path, sep=";", dtype=str)
        if df.empty: return None
        df["__key"] = df["Name"].apply(norm_name)
        row = df[df["__key"] == beacon_key]
        if row.empty: return None
        if "TxPower" not in row.columns: return None
        val = row.iloc[0]["TxPower"]
        return float(val) if pd.notna(val) and str(val).strip() != "" else None
    except Exception:
        return None

def est_distance_from_rssi(rssi: float, tx_power: float, n_env: float) -> float:
    # d = 10 ^ ((TxPower - RSSI)/(10*n))
    return float(10 ** ((tx_power - rssi) / (10.0 * max(n_env, 1e-6))))

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Live distance estimate to a single beacon (console)")
    ap.add_argument("--csv", default="telemetry_log.csv", help="Путь к telemetry_log.csv")
    ap.add_argument("--beacons", default="standart.beacons", help="Путь к файлу маяков (*.beacons)")
    ap.add_argument("--beacon", required=True, help="Имя маяка (как в JSON), напр. beacon5")
    ap.add_argument("--interval", type=float, default=0.1, help="Интервал обновления, сек")
    ap.add_argument("--window", type=int, default=60, help="Сколько последних строк CSV брать в окно")
    ap.add_argument("--n", type=float, default=2.0, help="Показатель затухания n")
    ap.add_argument("--txpower", type=float, default=None, help="Явно задать TxPower (RSSI@1м), переопределяет файл")
    args = ap.parse_args()

    csv_path = Path(args.csv).resolve()
    beacons_path = Path(args.beacons).resolve()
    bkey = norm_name(args.beacon)

    # определяем TxPower
    txp = args.txpower
    if txp is None:
        txp = try_load_txpower(beacons_path, bkey)
    if txp is None:
        txp = -59.0  # дефолт
        print(f"[INFO] TxPower для {args.beacon} не найден в {beacons_path}. Использую по умолчанию {txp:.1f} дБм.")
    else:
        print(f"[INFO] TxPower для {args.beacon}: {txp:.1f} дБм")

    print(f"[RUN] CSV={csv_path} | beacon={args.beacon} | n={args.n:.2f} | window={args.window} | interval={args.interval}s")
    print("Нажми Ctrl+C для выхода.\n")

    try:
        while True:
            recs = read_last_records(csv_path, max(1, args.window))
            vals = rssi_list_for_beacon(recs, bkey)
            if vals:
                rssi_med = float(np.median(vals))
                rssi_avg = float(np.mean(vals))
                rssi_std = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
                d_med = est_distance_from_rssi(rssi_med, txp, float(args.n))
                d_avg = est_distance_from_rssi(rssi_avg, txp, float(args.n))
                ts = recs[-1]["ts"] if recs else ""
                print(f"{ts}  RSSI_med={rssi_med:6.1f} dBm  RSSI_avg={rssi_avg:6.1f} dBm  σ={rssi_std:5.2f}  "
                      f"→ d_med≈{d_med:6.2f} m  d_avg≈{d_avg:6.2f} m")
            else:
                print("— нет измерений целевого маяка в окне —")
            time.sleep(max(0.01, float(args.interval)))
    except KeyboardInterrupt:
        print("\n[STOP] bye.")

if __name__ == "__main__":
    main()
