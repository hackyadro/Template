import os
from typing import Dict, Any
import sqlitedict
from .config import BACKEND_DB, BEACONS_FILE, PATH_OUT

# simple key-value store for incoming trackpoints
db = sqlitedict.SqliteDict(BACKEND_DB, autocommit=True)

def load_beacons(beacons_file=BEACONS_FILE) -> Dict[str,tuple]:
    anchors = {}
    if not os.path.exists(beacons_file):
        return anchors
    with open(beacons_file, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith("Name"):
                continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) >= 3:
                anchors[parts[0]] = (float(parts[1]), float(parts[2]))
    return anchors

def save_position(device_id: str, x: float, y: float, ts: int):
    key = f"track:{device_id}"
    arr = db.get(key, [])
    arr.append({"x":x,"y":y,"ts":ts})
    db[key] = arr
    # also append to path file (for hackathon export)
    with open(PATH_OUT, "a", encoding="utf-8") as f:
        f.write(f"{x};{y}\n")
