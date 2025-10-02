from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from .mqtt_consumer import start_mqtt_loop
from .persistence import load_beacons, db
from .config import BEACONS_FILE, PATH_OUT
import threading, time, os

app = FastAPI(title="Hackyadro Backend")

# start mqtt consumer in background thread on startup
@app.on_event("startup")
def startup_event():
    start_mqtt_loop()
    print("MQTT consumer started")

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/beacons")
def get_beacons():
    anchors = load_beacons(BEACONS_FILE)
    return anchors

@app.get("/tracks/{device_id}")
def get_track(device_id: str):
    key = f"track:{device_id}"
    arr = db.get(key, [])
    return {"device_id": device_id, "track": arr}

@app.post("/export/path")
def export_path():
    if not os.path.exists(PATH_OUT):
        raise HTTPException(404, "path not found")
    with open(PATH_OUT, "r", encoding="utf-8") as f:
        content = f.read()
    return JSONResponse(content={"path": content})
