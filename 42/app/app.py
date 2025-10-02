# app.py
# запуск: streamlit run app.py
from __future__ import annotations
import io, re, json, time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import streamlit as st

st.set_page_config(page_title="ESP32 Beacons — Single device", layout="wide")

# ---------- попытка подключить SciPy для LSQ ----------
try:
    from scipy.optimize import least_squares
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


# ============================ КОНСТАНТЫ (фикс) ============================
# Сглаживание траектории (фиксировано по твоей просьбе)
SMOOTH_ENABLE = True
CHA_ITERS     = 2
CHA_ALPHA     = 0.25
SHOW_RAW_PATH = False
WRITE_SMOOTHED_MOVAVG = False  # не используется (метод Chaikin фиксирован)

# Приём решения
DEFAULT_RMS_MAX_ACCEPT_M = 10.0  # дефолтный порог принятия решения по RMS

# ============================ УТИЛИТЫ ============================

def norm_name(s: str) -> str:
    if s is None: return ""
    return re.sub(r"[\s:\-_/]+", "", str(s).strip().lower())

def ensure_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        path.write_text("X;Y\n", encoding="utf-8")

def reset_path_keep_header(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("X;Y\n", encoding="utf-8")

def decode_csv_json_field(s: str) -> str:
    if s is None: return ""
    s = s.strip()
    if len(s) >= 2 and (s[0] == s[-1] == '"' or s[0] == s[-1] == "'"):
        s = s[1:-1]
    s = s.replace('""', '"').replace('\\"', '"')
    return s

def load_beacons(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p, sep=";", dtype=str)
    df["X"] = df["X"].str.replace(",", ".", regex=False).astype(float)
    df["Y"] = df["Y"].str.replace(",", ".", regex=False).astype(float)
    if "TxPower" in df.columns:
        df["TxPower"] = df["TxPower"].astype(float)
    else:
        df["TxPower"] = np.nan
    return df

def load_path_any_format(p: Path) -> pd.DataFrame:
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame(columns=["X", "Y"])
    txt = p.read_text(encoding="utf-8", errors="ignore")
    nums = re.findall(r'[-+]?\d+(?:\.\d+)?', txt)
    if len(nums) < 2:
        return pd.DataFrame(columns=["X", "Y"])
    vals = list(map(float, nums))
    if len(vals) % 2 == 1: vals = vals[:-1]
    xs = vals[0::2]; ys = vals[1::2]
    return pd.DataFrame({"X": xs, "Y": ys})

# ============================ МОДЕЛЬ ============================

def rssi_to_distance(rssi: float, tx_power: float, n_env: float) -> float:
    return 10 ** ((tx_power - rssi) / (10.0 * max(n_env, 1e-6)))

def trilaterate_lsq(anchors_xy: np.ndarray, dists: np.ndarray, iters: int = 25) -> tuple[np.ndarray, float]:
    D = np.maximum(dists, 1e-6)
    w = 1.0 / D**2
    p = (anchors_xy * w[:, None]).sum(axis=0) / w.sum()
    for _ in range(iters):
        dif = p - anchors_xy
        norm = np.linalg.norm(dif, axis=1) + 1e-9
        r = norm - D
        J = dif / norm[:, None]
        H = J.T @ J
        g = J.T @ r
        try:
            dp = -np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break
        p = p + dp
        if np.linalg.norm(dp) < 1e-5:
            break
    rms = float(np.sqrt(np.mean((np.linalg.norm(p - anchors_xy, axis=1) - D) ** 2)))
    return p, rms

def calculate_position(beacons: List[dict],
                       beacon_coords: Dict[str, Tuple[float, float]],
                       tx_map: Dict[str, float | None],
                       default_tx: float,
                       n_env: float) -> tuple[tuple[float, float] | None, float | None]:
    pts, D = [], []
    for b in beacons:
        nm = b["name"]
        if nm not in beacon_coords: continue
        (xi, yi) = beacon_coords[nm]
        txp = tx_map.get(nm) or default_tx
        di  = rssi_to_distance(float(b["rssi"]), float(txp), float(n_env))
        pts.append((xi, yi)); D.append(di)
    if len(pts) < 3: return None, None
    A = np.array(pts, float); D = np.array(D, float)
    w = 1.0 / np.maximum(D, 1e-6) ** 2
    p0 = (A * w[:, None]).sum(axis=0) / w.sum()
    if _HAVE_SCIPY:
        def resid(p):
            diff = p.reshape(1, 2) - A
            return np.linalg.norm(diff, axis=1) - D
        res = least_squares(resid, p0, method="lm")
        p = res.x; rms = float(np.sqrt(np.mean(res.fun ** 2)))
        return (float(p[0]), float(p[1])), rms
    else:
        p, rms = trilaterate_lsq(A, D, iters=25)
        return (float(p[0]), float(p[1])), rms

def solve_robust(beacons: List[dict],
                 beacon_coords: Dict[str, Tuple[float, float]],
                 tx_map: Dict[str, float|None],
                 default_tx: float,
                 n_env: float,
                 resid_thresh: float,
                 max_passes: int = 2) -> tuple[tuple[float, float] | None, float | None, List[dict]]:
    used = [b for b in beacons if b["name"] in beacon_coords]
    if len(used) < 3: return None, None, []
    for _ in range(max_passes + 1):
        pos, rms = calculate_position(used, beacon_coords, tx_map, default_tx, n_env)
        if pos is None: return None, None, []
        residuals = []
        for b in used:
            (x, y) = beacon_coords[b["name"]]
            txp = tx_map.get(b["name"]) or default_tx
            d = rssi_to_distance(b["rssi"], txp, n_env)
            r = abs(np.linalg.norm([pos[0]-x, pos[1]-y]) - d)
            residuals.append((r, b))
        worst = max(residuals, key=lambda t: t[0])
        if worst[0] > resid_thresh and len(used) > 3:
            used.remove(worst[1]); continue
        return pos, rms, used
    return pos, rms, used  # type: ignore

def ransac_position(beacons: List[dict],
                    beacon_coords: Dict[str, Tuple[float, float]],
                    tx_map: Dict[str, float|None],
                    default_tx: float,
                    n_env: float,
                    resid_thresh: float) -> tuple[tuple[float,float] | None, float | None, List[dict]]:
    cand = []
    usable = [b for b in beacons if b["name"] in beacon_coords]
    if len(usable) < 3: return None, None, []
    for m in (4, 3):
        if len(usable) < m: continue
        for comb in combinations(usable, m):
            pos, rms, used = solve_robust(list(comb), beacon_coords, tx_map, default_tx, n_env,
                                          resid_thresh=resid_thresh, max_passes=1)
            if pos is not None and rms is not None:
                cand.append((rms, pos, used))
    if not cand: return None, None, []
    cand.sort(key=lambda t: t[0])
    best = cand[0]
    return best[1], best[0], best[2]

def clamp_to_axes(pos: Tuple[float,float], axes: Tuple[float,float,float,float], margin: float) -> Tuple[float,float]:
    x_min, x_max, y_min, y_max = axes
    x_min -= margin; x_max += margin
    y_min -= margin; y_max += margin
    x = min(max(pos[0], x_min), x_max)
    y = min(max(pos[1], y_min), y_max)
    return (x, y)

# ============================ КАЛМАН (CV) ============================

class KalmanCV2D:
    def __init__(self, sigma_a: float = 1.5, r_meas: float = 1.2):
        self.x = np.zeros(4)   # [x,y,vx,vy]
        self.P = np.eye(4)
        self.sigma_a = float(sigma_a)
        self.r_meas = float(r_meas)
        self._inited = False

    def predict(self, dt: float):
        F = np.array([[1,0,dt,0],
                      [0,1,0,dt],
                      [0,0,1, 0],
                      [0,0,0, 1]], float)
        q = self.sigma_a**2
        G = np.array([[0.5*dt*dt, 0],
                      [0, 0.5*dt*dt],
                      [dt, 0],
                      [0, dt]], float)
        Q = G @ (np.eye(2)*q) @ G.T
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def update(self, z: np.ndarray):
        H = np.array([[1,0,0,0],
                      [0,1,0,0]], float)
        R = np.eye(2) * self.r_meas
        y = z.reshape(2,) - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ H) @ self.P

    def step(self, z: np.ndarray, dt: float) -> np.ndarray:
        if not self._inited:
            self.x[:2] = z.reshape(2,)
            self.P = np.eye(4)
            self._inited = True
            return self.x[:2].copy()
        self.predict(max(1e-3, float(dt)))
        self.update(z)
        return self.x[:2].copy()

# ============================ СГЛАЖИВАНИЕ TRAIL (Chaikin фикс) ============================

def smooth_chaikin(points: np.ndarray, iters: int = 2, alpha: float = 0.25) -> np.ndarray:
    if len(points) < 3: return points
    P = points.astype(float, copy=True)
    a = float(np.clip(alpha, 0.01, 0.49))
    for _ in range(max(1, iters)):
        Q = (1-a)*P[:-1] + a*P[1:]
        R = a*P[:-1] + (1-a)*P[1:]
        P = np.empty((Q.shape[0]+R.shape[0], 2), dtype=float)
        P[0::2] = Q; P[1::2] = R
    return P

# ============================ САЙДБАР (минимально нужное) ============================

st.sidebar.header("Файлы")
beacons_path = Path(st.sidebar.text_input("Файл маяков (*.beacons)", "standart.beacons")).resolve()
csv_path     = Path(st.sidebar.text_input("Файл телеметрии CSV", "telemetry_log.csv")).resolve()
path_out     = Path(st.sidebar.text_input("Файл маршрута (*.path)", "standart.path")).resolve()

st.sidebar.header("Управление")
c1, c2 = st.sidebar.columns(2)
with c1: start_click = st.button("▶ Start", type="primary")
with c2: stop_click  = st.button("■ Stop")

st.sidebar.header("Чтение/агрегация")
SLEEP_MS      = st.sidebar.slider("Пауза между чтениями, мс", 50, 2000, 200, 10)
WINDOW_LINES  = st.sidebar.number_input("Окно (последние строки CSV)", 10, 200000, 300, 10)
TOP_K         = st.sidebar.slider("Top-K маяков", 3, 10, 4, 1)

st.sidebar.header("Радио")
DEFAULT_TX    = st.sidebar.slider("TxPower (RSSI@1м), дБм", -80.0, -30.0, -59.0, 0.5)
N_ENV         = st.sidebar.slider("Показатель затухания n", 1.2, 4.0, 3.0, 0.1)  # дефолт = 3.0

st.sidebar.header("Робастность/фильтры")
RESID_THRESH_M   = st.sidebar.slider("Порог выброса по невязке, м", 0.5, 10.0, 2.5, 0.1)
RMS_MAX_ACCEPT_M = st.sidebar.slider("Макс. RMS принятия, м", 0.5, 20.0, DEFAULT_RMS_MAX_ACCEPT_M, 0.5)

st.sidebar.header("Калман (CV)")
SIGMA_A      = st.sidebar.slider("σ_a (шум ускорения), м/с²", 0.1, 5.0, 1.5, 0.1)
R_MEAS       = st.sidebar.slider("R (шум измерения), м²", 0.2, 5.0, 1.2, 0.1)

st.sidebar.header("Флаги")
USE_RANSAC   = st.sidebar.toggle("RANSAC по 3–4 маякам", True)
CLAMP_INSIDE = st.sidebar.toggle("Ограничивать внутри границ (+0.5м)", True)
AUTO_WRITE   = st.sidebar.toggle("Писать точки в .path", True)
DEBUG_LOG    = st.sidebar.toggle("Печатать расчёты в консоль", False)

# ============================ СОСТОЯНИЕ ============================

ss = st.session_state
ss.setdefault("running", False)
ss.setdefault("axes", None)
ss.setdefault("kf", None)
ss.setdefault("last_tsec", None)

if start_click:
    reset_path_keep_header(path_out)
    ss["kf"] = None
    ss["last_tsec"] = None
    ss["axes"] = None
    ss["running"] = True
    st.toast("Start: standart.path очищён (оставлена шапка).", icon="✅")

if stop_click:
    ss["running"] = False
    st.toast("Stop: запись маршрута остановлена.", icon="🛑")

# ============================ МАЯКИ И ГРАНИЦЫ ============================

left, right = st.columns([2, 1])

if not beacons_path.exists():
    with left: st.warning(f"Файл маяков не найден: {beacons_path}")
    beacons_df = pd.DataFrame(columns=["Name", "X", "Y", "TxPower"])
else:
    beacons_df = load_beacons(beacons_path)

beacon_coords: Dict[str, Tuple[float, float]] = {}
beacon_tx: Dict[str, float | None] = {}
for _, r in beacons_df.iterrows():
    key = norm_name(r["Name"])
    beacon_coords[key] = (float(r["X"]), float(r["Y"]))
    beacon_tx[key] = (float(r["TxPower"]) if "TxPower" in r and pd.notna(r["TxPower"]) else None)

def compute_square_bounds() -> Optional[tuple[float,float,float,float]]:
    xs, ys = [], []
    if len(beacons_df) > 0:
        xs += beacons_df["X"].tolist(); ys += beacons_df["Y"].tolist()
    if path_out.exists():
        pdf = load_path_any_format(path_out)
        if not pdf.empty:
            xs += pdf["X"].tolist(); ys += pdf["Y"].tolist()
    if not xs or not ys:
        return None
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    pad = 1.2
    x_min -= pad; x_max += pad; y_min -= pad; y_max += pad
    cx = (x_min + x_max)/2; cy = (y_min + y_max)/2
    span = max(x_max - x_min, y_max - y_min); half = span/2
    return (cx - half, cx + half, cy - half, cy + half)

if ss["axes"] is None:
    ss["axes"] = compute_square_bounds()

# ============================ CSV → ОДНО УСТРОЙСТВО ============================

def read_last_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, sep=",", dtype=str, on_bad_lines="skip")
        return df
    except Exception:
        return pd.DataFrame()

def parse_beacons_median(df: pd.DataFrame, window_lines: int) -> tuple[Dict[str,float], Optional[str]]:
    if df.empty: return {}, None
    tail = df.tail(int(window_lines))
    ts = tail["ts"].iloc[-1] if "ts" in tail.columns and len(tail)>0 else None
    bj_col = "beacons_json" if "beacons_json" in tail.columns else None
    if bj_col is None: return {}, ts
    bag: Dict[str, List[float]] = {}
    for _, r in tail.iterrows():
        s = decode_csv_json_field(str(r[bj_col]))
        try:
            arr = json.loads(s)
        except Exception:
            continue
        if not isinstance(arr, list): continue
        for it in arr:
            if not isinstance(it, dict): continue
            name_raw = it.get("name") or it.get("id") or it.get("beacon") or it.get("mac")
            rssi_val = it.get("rssi")
            if name_raw is None or rssi_val is None: continue
            k = norm_name(str(name_raw))
            bag.setdefault(k, []).append(float(rssi_val))
    med = {k: float(np.median(v)) for k, v in bag.items() if v}
    return med, ts

def parse_tsec(ts: str) -> Optional[float]:
    try:
        hh = int(ts[11:13]); mm = int(ts[14:16]); ss_ = float(ts[17:])
        return hh*3600 + mm*60 + ss_
    except Exception:
        return None

# ============================ ОДИН ШАГ ОЦЕНКИ ============================

def compute_once() -> tuple[Optional[Tuple[float,float]], Optional[float], List[dict], Optional[str]]:
    df = read_last_dataframe(csv_path)
    med, ts = parse_beacons_median(df, WINDOW_LINES)
    blist = [{"name": k, "rssi": v} for k, v in med.items()]
    blist.sort(key=lambda x: x["rssi"], reverse=True)
    blist = blist[:int(TOP_K)]

    if not blist: return None, None, [], ts

    if USE_RANSAC:
        pos, rms, used = ransac_position(blist, beacon_coords, beacon_tx, DEFAULT_TX, N_ENV, RESID_THRESH_M)
    else:
        pos, rms, used = solve_robust(blist, beacon_coords, beacon_tx, DEFAULT_TX, N_ENV, RESID_THRESH_M, max_passes=2)

    if pos is not None and rms is not None and rms > float(RMS_MAX_ACCEPT_M):
        pos = None

    if pos is not None and CLAMP_INSIDE and ss["axes"] is not None:
        pos = clamp_to_axes(pos, ss["axes"], 0.5)

    # Калман для одного устройства
    if pos is not None:
        if ss["kf"] is None:
            ss["kf"] = KalmanCV2D(sigma_a=float(SIGMA_A), r_meas=float(R_MEAS))
        dt = float(SLEEP_MS)/1000.0
        if ts is not None:
            tsec = parse_tsec(ts)
            if tsec is not None:
                if ss["last_tsec"] is not None:
                    dt = max(1e-3, tsec - float(ss["last_tsec"]))
                ss["last_tsec"] = tsec
        pos = tuple(ss["kf"].step(np.array(pos, float), dt))  # type: ignore

    return pos, rms, blist, ts

# ============================ ОТРИСОВКА ============================

def draw(ax, pos: Optional[Tuple[float,float]]):
    if ss["axes"] is not None:
        x_min, x_max, y_min, y_max = ss["axes"]
        ax.set_xlim(x_min, x_max); ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal", adjustable="box")

    ax.xaxis.set_major_locator(MultipleLocator(6.0))
    ax.yaxis.set_major_locator(MultipleLocator(6.0))
    ax.xaxis.set_minor_locator(MultipleLocator(0.6))
    ax.yaxis.set_minor_locator(MultipleLocator(0.6))
    ax.grid(True, which="major", linewidth=0.7, color=(0.5,0.5,0.5), alpha=0.35)
    ax.grid(True, which="minor", linewidth=0.5, color=(0.7,0.7,0.7), alpha=0.2)

    # маяки
    if beacon_coords:
        xs = [v[0] for v in beacon_coords.values()]
        ys = [v[1] for v in beacon_coords.values()]
        labels = list(beacon_coords.keys())
        ax.scatter(xs, ys, marker="s")
        for (x, y), name in zip(beacon_coords.values(), labels):
            ax.text(x, y, name, fontsize=8)

    # путь
    if path_out.exists():
        pdf = load_path_any_format(path_out)
        if not pdf.empty:
            pts = pdf[["X","Y"]].to_numpy()
            if SHOW_RAW_PATH:
                ax.plot(pts[:,0], pts[:,1], color=(0.5,0.5,0.5,0.6), linewidth=1.0, zorder=1)
            if SMOOTH_ENABLE:
                spts = smooth_chaikin(pts, iters=CHA_ITERS, alpha=CHA_ALPHA)
                ax.plot(spts[:,0], spts[:,1], color="C0", linewidth=1.8, zorder=2)
            else:
                ax.plot(pts[:,0], pts[:,1], color="C0", linewidth=1.4, zorder=2)

    # текущая точка
    if pos is not None:
        ax.scatter([pos[0]], [pos[1]], s=90, color="orange", edgecolor="black", linewidths=0.6, zorder=5)

    ax.set_xlabel("X"); ax.set_ylabel("Y")
    ax.set_title("Beacons & Device — single, LSQ + Kalman (Chaikin smooth fixed)")

# ============================ ГЛАВНЫЙ ШАГ/ЦИКЛ ============================

position, rms, used_beacons, ts_sel = (None, None, [], None)
if ss["running"]:
    position, rms, used_beacons, ts_sel = compute_once()
    if AUTO_WRITE and position is not None:
        ensure_header(path_out)
        with path_out.open("a", encoding="utf-8") as f:
            f.write(f"{position[0]:.6f};{position[1]:.6f}\n")
            f.flush()

# визуал
left.subheader("Карта (квадрат, сетка 0.6)")
fig = plt.figure(figsize=(8, 8))
ax = plt.gca()
draw(ax, position)
left.pyplot(fig, clear_figure=False)

buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
left.download_button("Сохранить PNG", data=buf.getvalue(),
                     file_name="beacons_single.png", mime="image/png")

# статус
right.subheader("Статус")
right.write(f"CSV: `{csv_path}`")
right.write(f"Считывание: **{'идёт' if ss['running'] else 'остановлено'}**")
right.write(f"Маяков: **{len(beacon_coords)}**")
if position is not None:
    txt_rms = f" | RMS≈{rms:.3f}" if rms is not None else ""
    right.success(f"📍 X={position[0]:.3f}, Y={position[1]:.3f}{txt_rms}")
else:
    right.info("Нет оценки позиции (или отклонена по RMS/данных мало).")

# цикл
time.sleep(max(0.01, float(SLEEP_MS)/1000.0) if ss["running"] else 0.05)
try:
    st.rerun()
except AttributeError:
    st.experimental_rerun()
