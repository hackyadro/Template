import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class ConfigLoader:
    def __init__(self, config_dir: str = "data/maps"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_beacons_from_csv(self, map_file: str, delimiter: str = ";") -> List[Dict[str, Any]]:
        return self._load_csv(Path(self.config_dir / map_file), delimiter)

    def load_beacons(self, map_id: str, delimiter: str = ";") -> List[Dict[str, Any]]:
        """Сначала ищем {mapId}.csv, затем {mapId}.beacons (оба — CSV с ';')."""
        csv_path = self.config_dir / f"{map_id}.csv"
        bea_path = self.config_dir / f"{map_id}.beacons"
        if csv_path.exists():
            return self._load_csv(csv_path, delimiter)
        if bea_path.exists():
            return self._load_csv(bea_path, delimiter)
        raise FileNotFoundError(f"Map files not found: {csv_path.name} or {bea_path.name}")

    def _load_csv(self, path: Path, default_delimiter: str) -> List[Dict[str, Any]]:
        beacons: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            sample = f.read(2048)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=";, \t")
                delimiter = dialect.delimiter
            except Exception:
                delimiter = default_delimiter or ";"
            has_header = csv.Sniffer().has_header(sample)

            if has_header:
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    b = self._parse_beacon_row(row)
                    if b:
                        beacons.append(b)
            else:
                reader = csv.reader(f, delimiter=delimiter)
                for row in reader:
                    if len(row) >= 3:
                        beacons.append({
                            "id": row[0].strip(),
                            "x": float(row[1]),
                            "y": float(row[2])
                        })
        return beacons

    def _parse_beacon_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            name = row.get("Name") or row.get("name") or list(row.values())[0]
            x = float(row.get("X") or row.get("x") or list(row.values())[1])
            y = float(row.get("Y") or row.get("y") or list(row.values())[2])
            return {"id": str(name).strip(), "x": x, "y": y}
        except Exception as e:
            print(f"Warning: Failed to parse beacon row {row}: {e}")
            return None

    def save_path_to_file(self, positions: List[Dict[str, Any]], filename: str, session_id: str):
        """Сохраняет маршрут в .path файл"""
        paths_dir = Path("data/paths")
        paths_dir.mkdir(parents=True, exist_ok=True)

        path_data = {
            "sessionId": session_id,
            "startTime": positions[0]["timestamp"] if positions else 0,
            "endTime": positions[-1]["timestamp"] if positions else 0,
            "points": [
                {"x": p["x"], "y": p["y"], "t": p.get("timestamp", 0)} for p in positions
            ],
        }

        file_path = paths_dir / f"{filename}.path"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(path_data, f, indent=2, ensure_ascii=False)

        return file_path
