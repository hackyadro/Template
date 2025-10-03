# app_simple.py
from __future__ import annotations
import os, io, json, time, re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import streamlit as st

try:
    from scipy.optimize import least_squares as _least_squares
except Exception:
    _least_squares = None

# SETTINGS

WINDOW_LINES = 50
N_ENV        = 3.0
RSSI0        = -43.0
TOPK_SOLVER  = 3
KF_Q         = 0.1
KF_R         = 1.0
GRID_STEP    = 0.6
MAJOR_STEP   = 6.0

K_MAD                  = 3.5
TRIM_FRAC              = 0.1
MIN_SAMPLES_PER_BEACON = 4
HUBER_DELTA            = 1.0
LSQ_F_SCALE            = 1.0

st.set_page_config(page_title="Beacons & Devices", layout="wide")

# UTILS

def norm_name(s: str) -> str:
    return re.sub(r"[\s:\-_/]+", "", str(s).strip().lower()) if s is not None else ""

def ensure_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        path.write_text("X;Y\n", encoding="utf-8")

def load_beacons(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame(columns=["Name", "X", "Y"])
    df = pd.read_csv(p, sep=";", dtype=str)
    df["X"] = df["X"].str.replace(",", ".", regex=False).astype(float)
    df["Y"] = df["Y"].str.replace(",", ".", regex=False).astype(float)
    return df

def fixed_square_bounds(beacons_df: pd.DataFrame, paths_dir: Path) -> Optional[Tuple[float,float,float,float]]:
    xs, ys = [], []
    if not beacons_df.empty:
        xs += beacons_df["X"].tolist(); ys += beacons_df["Y"].tolist()
    if paths_dir.exists():
        for fp in paths_dir.glob("*.path"):
            try:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
                nums = list(map(float, re.findall(r"[-+]?\d+(?:\.\d+)?", txt)))
                xs += nums[0::2]; ys += nums[1::2]
            except Exception:
                pass
    if not xs or not ys:
        return None
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    pad = 5
    x0 -= pad; x1 += pad; y0 -= pad; y1 += pad
    cx, cy = (x0+x1)/2, (y0+y1)/2
    span = max(x1-x0, y1-y0)
    half = span/2
    return (cx-half, cx+half, cy-half, cy+half)

# CSV IO

def read_tail_lines(path: Path, n: int) -> List[str]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    block = 8192
    need = n + 1
    data = b""
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        while pos > 0 and need > 0:
            step = block if pos >= block else pos
            pos -= step
            f.seek(pos)
            buf = f.read(step)
            data = buf + data
            lines = [ln for ln in data.splitlines() if ln.strip()]
            need = (n + 1) - len(lines)
            if need <= 0:
                break
    lines = [ln.decode("utf-8", errors="ignore") for ln in data.splitlines() if ln.strip()]
    with path.open("rb") as f:
        eof_nl = f.read().endswith(b"\n")
    if lines and not eof_nl:
        lines = lines[:-1]
    return lines[-n:]

# CSV PARSING

def parse_one_line(line: str) -> Optional[dict]:
    parts = line.strip().split(",", 6)
    if len(parts) < 7:
        return None
    return {
        "ts": parts[0].strip(),
        "device_id": parts[1].strip(),
        "seq": parts[2].strip(),
        "ip": parts[3].strip(),
        "uptime_s": parts[4].strip(),
        "rssi": parts[5].strip(),
        "beacons_json": parts[6].strip(),
    }

def decode_bj(s: str) -> List[dict]:
    s = s.strip()
    if len(s) >= 2 and (s[0] == s[-1] == '"' or s[0] == s[-1] == "'"):
        s = s[1:-1]
    s = s.replace('""', '"').replace('\\"', '"')
    try:
        arr = json.loads(s)
        return arr if isinstance(arr, list) else []
    except Exception:
        return []

def robust_median(arr: List[float]) -> Optional[float]:
    v = np.asarray(arr, dtype=float)
    if v.size == 0:
        return None
    m = np.median(v)
    mad = np.median(np.abs(v - m))
    thr = 1.4826 * mad * K_MAD
    if thr == 0:
        keep = v
    else:
        keep = v[np.abs(v - m) <= thr]
    if keep.size == 0:
        return None
    keep.sort()
    cut = int(np.floor(TRIM_FRAC * keep.size))
    if cut > 0:
        keep = keep[cut:-cut] if keep.size - 2*cut > 0 else keep
    if keep.size < MIN_SAMPLES_PER_BEACON:
        return None
    return float(np.median(keep))

def median_rssi_per_device_tail(path: Path, n_lines: int) -> Dict[str, dict]:
    lines = read_tail_lines(path, n_lines)
    if not lines:
        return {}
    by_dev: Dict[str, dict] = {}
    for ln in lines:
        rec = parse_one_line(ln)
        if not rec:
            continue
        dev = rec["device_id"] or "dev"
        by_dev.setdefault(dev, {"ts": rec["ts"], "bag": {}})
        for it in decode_bj(rec["beacons_json"]):
            name_raw = it.get("name") or it.get("id") or it.get("beacon") or it.get("mac")
            rssi_val = it.get("rssi")
            if name_raw is None or rssi_val is None:
                continue
            k = norm_name(name_raw)
            by_dev[dev]["bag"].setdefault(k, []).append(float(rssi_val))
    out: Dict[str, dict] = {}
    for dev, d in by_dev.items():
        bag = d["bag"]
        if not bag:
            continue
        rssi_med = {}
        for k, v in bag.items():
            rm = robust_median(v)
            if rm is not None:
                rssi_med[k] = rm
        if not rssi_med:
            continue
        out[dev] = {"ts": d["ts"], "rssi_med": rssi_med}
    return out

# POSITION SOLVER

def rssi_to_distance(rssi: float) -> float:
    return 10.0 ** ((RSSI0 - float(rssi)) / (10.0 * max(N_ENV, 1e-6)))

def trilaterate_lsq_numpy(anchors_xy: np.ndarray, dists: np.ndarray, iters: int = 50) -> np.ndarray:
    p = anchors_xy.mean(axis=0).astype(float)
    D = np.maximum(dists.astype(float), 1e-6)
    for _ in range(iters):
        dif = p - anchors_xy
        norm = np.linalg.norm(dif, axis=1)
        r = norm - D
        J = dif / (norm[:, None] + 1e-9)
        H = J.T @ J
        g = J.T @ r
        try:
            dp = -np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break
        p = p + dp
        if np.linalg.norm(dp) < 1e-5:
            break
    return p

class KalmanFilter2D:
    def __init__(self, q=0.1, r=1.0):
        self.x = np.zeros(2, dtype=float)
        self.P = np.eye(2, dtype=float)
        self.Q = np.eye(2, dtype=float) * float(q)
        self.R = np.eye(2, dtype=float) * float(r)

    def update(self, z: np.ndarray) -> np.ndarray:
        self.P = self.P + self.Q
        S = self.P + self.R
        K = self.P @ np.linalg.inv(S)
        self.x = self.x + K @ (z - self.x)
        self.P = (np.eye(2) - K) @ self.P
        return self.x.copy()

# UI

st.sidebar.header("Файлы")
beacons_path = Path(st.sidebar.text_input("Файл маяков (*.beacons)", "standart.beacons")).resolve()
csv_path     = Path(st.sidebar.text_input("Файл телеметрии CSV", "telemetry_log.csv")).resolve()
paths_dir    = Path(st.sidebar.text_input("Каталог путей", "paths")).resolve()

st.sidebar.header("Управление")
colA, colB = st.sidebar.columns(2)
with colA: start_click = st.button("▶ Start", type="primary")
with colB: stop_click  = st.button("■ Stop")
hz = st.sidebar.slider("Частота обработки, Гц", 0.1, 10.0, 5.0, 0.1)

ss = st.session_state
ss.setdefault("running", False)
ss.setdefault("bounds", None)
ss.setdefault("kf", {})
ss.setdefault("positions", {})
ss.setdefault("next_t", None)
ss.setdefault("last_png", None)

if start_click:
    ss["running"] = True
    paths_dir.mkdir(parents=True, exist_ok=True)
    for fp in paths_dir.glob("*.path"):
        fp.write_text("X;Y\n", encoding="utf-8")
if stop_click:
    ss["running"] = False

left, right = st.columns([3, 1])

# DATA PREP

beacons_df = load_beacons(beacons_path)
beacon_xy: Dict[str, Tuple[float,float]] = {norm_name(r["Name"]): (float(r["X"]), float(r["Y"])) for _, r in beacons_df.iterrows()}

if ss["bounds"] is None:
    ss["bounds"] = fixed_square_bounds(beacons_df, paths_dir)

# SOLVER WRAPPER

def estimate_position_lsq_kf(dev_id: str, rssi_map: Dict[str, float]) -> Optional[Tuple[float, float]]:
    items = [(name, rssi) for name, rssi in rssi_map.items() if name in beacon_xy]
    if len(items) < 3:
        return None
    items.sort(key=lambda x: x[1], reverse=True)
    items = items[:TOPK_SOLVER]
    anchors = np.array([beacon_xy[name] for name, _ in items], dtype=float)
    dists   = np.array([rssi_to_distance(rssi) for _, rssi in items], dtype=float)
    x0 = anchors.mean(axis=0)
    if _least_squares is not None:
        def resid(p):
            return np.linalg.norm(p - anchors, axis=1) - dists
        try:
            res = _least_squares(resid, x0, method="trf", loss="soft_l1", f_scale=LSQ_F_SCALE, max_nfev=100)
            raw = res.x.astype(float)
        except Exception:
            raw = trilaterate_lsq_numpy(anchors, dists)
    else:
        raw = trilaterate_lsq_numpy(anchors, dists)
    kf_map: Dict[str, KalmanFilter2D] = ss["kf"]
    if dev_id not in kf_map:
        kf_map[dev_id] = KalmanFilter2D(q=KF_Q, r=KF_R)
        kf_map[dev_id].x = raw.copy()
    filt = kf_map[dev_id].update(raw)
    return float(filt[0]), float(filt[1])

# PROCESS

def process_all_devices(write_paths: bool) -> Dict[str, Tuple[float,float]]:
    positions_now: Dict[str, Tuple[float,float]] = {}
    dev_map = median_rssi_per_device_tail(csv_path, WINDOW_LINES)
    for dev_id, d in dev_map.items():
        pos = estimate_position_lsq_kf(dev_id, d["rssi_med"])
        if pos is None:
            continue
        positions_now[dev_id] = pos
        if write_paths:
            out = paths_dir / f"{dev_id}.path"
            ensure_header(out)
            with out.open("a", encoding="utf-8") as f:
                f.write(f"{pos[0]:.6f};{pos[1]:.6f}\n")
    return positions_now

if ss["running"]:
    ss["positions"] = process_all_devices(write_paths=True)
positions = ss["positions"]

# PLOT

def draw(ax):
    if ss.get("bounds") is not None:
        x0, x1, y0, y1 = ss["bounds"]
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_locator(MultipleLocator(MAJOR_STEP))
    ax.yaxis.set_major_locator(MultipleLocator(MAJOR_STEP))
    ax.xaxis.set_minor_locator(MultipleLocator(GRID_STEP))
    ax.yaxis.set_minor_locator(MultipleLocator(GRID_STEP))
    ax.grid(True, which="major", linewidth=0.7, alpha=0.35)
    ax.grid(True, which="minor", linewidth=0.3, alpha=0.2)
    if not beacons_df.empty:
        xs = beacons_df["X"].tolist()
        ys = beacons_df["Y"].tolist()
        labels = [norm_name(n) for n in beacons_df["Name"].tolist()]
        ax.scatter(xs, ys, marker="s")
        for x, y, name in zip(xs, ys, labels):
            ax.text(x, y, name, fontsize=8)
    if paths_dir.exists():
        for fp in sorted(paths_dir.glob("*.path")):
            try:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
                vals = list(map(float, re.findall(r"[-+]?\d+(?:\.\d+)?", txt)))
                X, Y = vals[0::2], vals[1::2]
                if X and Y:
                    ax.plot(X, Y, linewidth=1.2)
            except Exception:
                pass
    for dev, (x, y) in positions.items():
        ax.scatter([x], [y], s=80, color="orange", edgecolor="black", linewidths=0.5, zorder=5, label=f"{dev}•now")
    if positions:
        ax.legend(loc="upper left", fontsize=8)
    ax.set_xlabel("X"); ax.set_ylabel("Y")
    ax.set_title(f"Beacons & Devices")

if "plot_slot" not in st.session_state:
    st.session_state["plot_slot"] = left.empty()
plot_slot = st.session_state["plot_slot"]

def render_plot():
    fig = plt.figure(figsize=(8, 8))
    ax = plt.gca()
    draw(ax)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    ss["last_png"] = buf.getvalue()
    plot_slot.image(ss["last_png"])
    plt.close(fig)

render_plot()

# STATUS

right.header("Статус")
right.write(f"CSV: `{csv_path}`")
right.write(f"Пути: `{paths_dir}`")
right.write(f"Считывание: **{'идёт' if ss['running'] else 'остановлено'}**")
right.write(f"Маяков в файле: **{len(beacon_xy)}**")
for dev, (x, y) in positions.items():
    right.success(f"{dev}: X={x:.3f}, Y={y:.3f}")
if ss.get("last_png"):
    right.download_button(
        label="⬇️ Скачать PNG",
        data=ss["last_png"],
        file_name=f"beacons_{int(time.time())}.png",
        mime="image/png",
        use_container_width=True,
    )
else:
    right.info("Изображение ещё не сгенерировано.")

# LOOP

period = max(0.05, 1.0/float(hz))
now = time.perf_counter()
if ss["next_t"] is None:
    ss["next_t"] = now + period
sleep_for = max(0.0, ss["next_t"] - now)
time.sleep(sleep_for)
ss["next_t"] += period

try:
    st.rerun()
except AttributeError:
    st.experimental_rerun()
