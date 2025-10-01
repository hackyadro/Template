# solver_api.py
# pip install fastapi uvicorn pydantic numpy
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import json

from position import estimate_xy

# Загружаем маяки (Name;X;Y)
def load_beacons(path="standart.beacons"):
    m = {}
    with open(path, "r", encoding="utf-8") as f:
        next(f)  # skip header
        for ln in f:
            name, xs, ys = [x.strip() for x in ln.split(";")[:3]]
            x = float(xs.replace(",", "."))
            y = float(ys.replace(",", "."))
            m[name] = (x, y)
    return m

BEACONS = load_beacons("standart.beacons")
PATH_FILE = Path("standart.path")

class Reading(BaseModel):
    name: str
    rssi: float

class RSSIPayload(BaseModel):
    ts: int
    readings: list[Reading]

app = FastAPI()

def append_path(x, y):
    if not PATH_FILE.exists():
        PATH_FILE.write_text("X;Y\n", encoding="utf-8")
    with PATH_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{x:.6f};{y:.6f}\n")

@app.post("/rssi")
def rssi(payload: RSSIPayload):
    # преобразуем в dict name->rssi (можно ещё медианить/EMA)
    rssi_map = {}
    for r in payload.readings:
        rssi_map[r.name] = rssi_map.get(r.name, r.rssi)

    try:
        x, y = estimate_xy(BEACONS, rssi_map)
        append_path(x, y)
        return {"ok": True, "x": x, "y": y}
    except Exception as e:
        return {"ok": False, "error": str(e)}
