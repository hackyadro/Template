import csv
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import pathlib

from app_state import GlobalState, AppStates
from data import db
import math
import time
from typing import List
import random

start_time = time.time()

app = FastAPI()

positions: List[dict] = []

# Абсолютный путь к каталогу "static" (src/backend/fastapi_app/static)
static_path = pathlib.Path(__file__).parent / "static"
data_path = pathlib.Path(__file__).parent.parent / "data" / "beacons.txt"

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory=static_path), name="static")
global_state = GlobalState()


@app.get("/", response_class=HTMLResponse)
async def root():
    index_file = static_path / "index.html"
    return index_file.read_text(encoding="utf-8")


@app.post("/api/delete_last_way")
async def delete_route():
    db.session.query(db.BoardPosition).delete()
    return {}


@app.post("/api/start_way")
async def start_route():
    global_state.set_state(AppStates.WRITE_WAY)
    db.session.query(db.BoardPosition).delete()
    print("Start route")
    return {}


@app.post("/api/finish_way")
async def finish_route():
    global_state.set_state(AppStates.WAITING)
    print("Stoppp route")
    return {}

@app.post("/api/upload_beacons")
async def upload_beacons(file: UploadFile = File(...)):
    """
    Перезаписывает beacons.txt содержимым загруженного файла.
    """
    if not file.filename.endswith(".txt"):
        return JSONResponse(content={"error": "Неверный формат файла"}, status_code=400)

    content = await file.read()
    # сохраняем в beacons.txt
    data_path.write_bytes(content)
    return {"status": "ok", "message": f"Файл {file.filename} успешно загружен"}


@app.get("/api/check_board")
async def check_payment():
    return {"res": global_state.is_board_turn_on()}



@app.get("/api/get_positions")
async def get_positions():
    pos_objs = db.session.query(db.BoardPosition).all()
    positions = [i.to_dict() for i in pos_objs]
    print(f"POSITIONS RETURN = {len(positions)}")
    res = {"positions" : positions}
    return JSONResponse(content=res)

@app.get("/api/get_positions_1")
async def get_positions_1():
    global positions
    # добавляем новую случайную точку каждые 2 секунды
    if not positions:
        new_pos = {"x": random.uniform(0, 0), "y": random.uniform(0, 0)}
    else:
        last = positions[-1]
        new_pos = {
            "x": last["x"] + random.uniform(-15, 15),
            "y": last["y"] + random.uniform(-15, 15),
        }
    positions.append(new_pos)
    return JSONResponse(content={"positions": positions})

@app.get("/api/beacons")
async def get_beacons():
    """
    Returns JSON: {"beacons": [{"id":"1","name":"beacon_1","x":3.0,"y":-2.4}, ...]}
    Robust against header line and malformed rows.
    """
    beacons = []
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=";")
            for row in reader:
                if not row:
                    continue
                # skip header
                first = row[0].strip().lower()
                if first == "name" or first.startswith("#"):
                    continue
                if len(row) < 3:
                    continue
                name = row[0].strip()
                xs = row[1].strip()
                ys = row[2].strip()
                try:
                    x = float(xs); y = float(ys)
                except Exception:
                    continue
                m = re.search(r"(\d+)$", name)
                id_ = m.group(1) if m else name
                beacons.append({"id": str(id_), "name": name, "x": x, "y": y})
    return JSONResponse(content={"beacons": beacons})