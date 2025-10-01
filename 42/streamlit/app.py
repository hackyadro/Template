# app.py
# streamlit run app.py
from threading import Thread

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import threading, time, io, sys
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

try:
    import serial  # pyserial
except Exception:
    serial = None

st.set_page_config(page_title="ESP32-C3 Beacons Tracker", layout="wide")

# ---------- утилиты ----------
def normalize_num(s: str) -> str:
    return s.replace(",", ".").strip()

def ensure_header(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        path.write_text("X;Y\n", encoding="utf-8")

def load_beacons(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p, sep=";", dtype=str)
    df["X"] = df["X"].str.replace(",", ".", regex=False).astype(float)
    df["Y"] = df["Y"].str.replace(",", ".", regex=False).astype(float)
    return df

def load_path(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame(columns=["X", "Y"])
    df = pd.read_csv(p, sep=";", dtype=str)
    if df.empty:
        return pd.DataFrame(columns=["X", "Y"])
    df["X"] = df["X"].str.replace(",", ".", regex=False).astype(float)
    df["Y"] = df["Y"].str.replace(",", ".", regex=False).astype(float)
    return df

# ---------- поток-сборщик ----------
def collector_worker(port: str, baud: int, out_path: Path, stop_event: threading.Event):
    """Читает строки 'x;y' с Serial и дописывает в out_path. Останавливается по stop_event."""
    ensure_header(out_path)
    ser = None
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=2)  # type: ignore[attr-defined]
        with out_path.open("a", encoding="utf-8") as f:
            while not stop_event.is_set():
                line = ser.readline().decode(errors="ignore")
                if not line:
                    continue
                if line.strip().upper() == "STOP":
                    break
                parts = line.split(";")
                if len(parts) < 2:
                    continue
                xs, ys = normalize_num(parts[0]), normalize_num(parts[1])
                try:
                    float(xs); float(ys)  # валидация
                    f.write(f"{xs};{ys}\n"); f.flush()
                except Exception:
                    # пропускаем битые пакеты
                    pass
    except Exception as e:
        st.session_state["collector_error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            if ser: ser.close()
        except Exception:
            pass
        st.session_state["collector_running"] = False

# ---------- состояние ----------
ss = st.session_state
ss.setdefault("collector_running", False)
ss.setdefault("collector_stop", None)
ss.setdefault("collector_thread", None)
ss.setdefault("collector_file", "standart.path")
ss.setdefault("collector_error", "")

# ---------- сайдбар-настройки ----------
st.sidebar.header("Файлы и подключение")
beacons_path = Path(st.sidebar.text_input("Файл маяков (*.beacons)", "standart.beacons"))

default_port = "COM5" if sys.platform.startswith("win") else "/dev/ttyUSB0"
port = st.sidebar.text_input("Serial порт", default_port)
baud = st.sidebar.number_input("Baud", 9600, 921600, 115200, 9600)

new_file_each_run = st.sidebar.toggle("Новый файл на каждый старт", True)
target_path = st.sidebar.text_input("Файл маршрута (*.path)",
                                    ss["collector_file"] if not new_file_each_run else "standart.path")

freq = st.sidebar.slider("Частота обновления графика, Гц", 0.1, 10.0, 2.0, 0.1)
live = st.sidebar.toggle("Живой режим", True)

# ---------- кнопки управления ----------
colA, colB = st.columns(2)
with colA:
    start_click = st.button("▶ Start", type="primary", disabled=ss["collector_running"])
with colB:
    stop_click = st.button("■ Stop", disabled=not ss["collector_running"])

# ---------- логика старт/стоп ----------
if start_click and not ss["collector_running"]:
    # Выбираем файл
    out = Path(target_path)
    if out.suffix.lower() != ".path" or out.name in ("", ".path") or out.as_posix().endswith("/"):
        # если указана папка или нет имени — создаём новый файл в папке
        folder = out if out.suffix == "" else out.parent
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / f"route_{datetime.now():%Y%m%d_%H%M%S}.path"
    ss["collector_file"] = str(out)

    # Проверка pyserial
    if serial is None:
        st.error("pyserial не установлен: pip install pyserial")
    else:
        ss["collector_error"] = ""
        ss["collector_stop"] = threading.Event()
        th = threading.Thread(
            target=collector_worker,
            args=(port, int(baud), out, ss["collector_stop"]),
            daemon=True,
        )
        th.start()
        ss["collector_thread"] = th
        ss["collector_running"] = True
        st.toast(f"Сбор запущен → {out}", icon="✅")

if stop_click and ss["collector_running"]:
    ss["collector_stop"].set()  # type: ignore[union-attr]
    if ss["collector_thread"]:
        ss["collector_thread"].join(timeout=2)
    ss["collector_running"] = False
    st.toast("Сбор остановлен", icon="🛑")

# ---------- интерфейс ----------
left, right = st.columns([2, 1])

with left:
    st.subheader("Карта")
    fig = plt.figure(figsize=(6, 6))
    ax = plt.gca()

    if beacons_path.exists():
        bdf = load_beacons(beacons_path)
        ax.scatter(bdf["X"], bdf["Y"], marker="s")
        for _, r in bdf.iterrows():
            ax.text(r["X"], r["Y"], str(r["Name"]), fontsize=8)
    else:
        st.warning("Файл маяков не найден.")

    current_path = Path(ss["collector_file"])
    pdf = load_path(current_path)
    if not pdf.empty:
        ax.plot(pdf["X"], pdf["Y"])
        st.caption(f"Точек в маршруте: {len(pdf)}")
        st.write(f"Последняя точка: ({pdf['X'].iloc[-1]:.3f}, {pdf['Y'].iloc[-1]:.3f})")
    else:
        st.info("Маршрут пока пуст.")

    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_title("Beacons & Path")
    ax.axis("equal"); ax.grid(True)
    st.pyplot(fig, clear_figure=False)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    st.download_button("Сохранить картинку PNG", data=buf.getvalue(),
                       file_name="route_snapshot.png", mime="image/png")

with right:
    st.subheader("Статус")
    st.write(f"Файл маршрута: **{ss['collector_file']}**")
    if ss["collector_running"]:
        st.success("Сбор идёт…")
    else:
        st.info("Сбор остановлен.")
    if ss["collector_error"]:
        st.error(ss["collector_error"])

# автообновление без сторонних пакетов
if live:
    time.sleep(max(0.1, 1.0/float(freq)))
    try:
        st.rerun()                 # Streamlit ≥1.26
    except AttributeError:
        st.experimental_rerun()    # старые версии