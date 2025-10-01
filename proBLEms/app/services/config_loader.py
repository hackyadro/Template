import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

class ConfigLoader:
    """
    Читает beacons из ./<mapId>.beacons (CSV) и пишет трек в ./<filename>.path (CSV).
    Форматы:
      *.beacons: Name;X;Y   (разделитель авто: ; , или таб)
      *.path:    X;Y        (CSV с ;, строка = точка)
    """
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parents[2]
        else:
            self.base_dir = Path(base_dir)

    # ---------- BEACONS ----------
    def load_beacons(self, map_id: str, default_delimiter: str = ";") -> List[Dict[str, Any]]:
        """
        Ищем только в корне проекта: ./<map_id>.beacons
        """
        path = (self.base_dir / f"{map_id}.beacons").resolve()
        if not path.exists():
            raise FileNotFoundError(f"Map file not found: {path.name} (expect in project root)")
        return self._load_beacons_csv(path, default_delimiter)

    def _load_beacons_csv(self, path: Path, default_delimiter: str) -> List[Dict[str, Any]]:
        beacons: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            sample = f.read(2048)
            f.seek(0)
            # автоопределение разделителя
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
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
                            "id": str(row[0]).strip(),
                            "x": float(row[1]),
                            "y": float(row[2]),
                        })
        if not beacons:
            raise ValueError(f"No beacons parsed from {path}")
        return beacons

    def _parse_beacon_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Поддерживаем заголовки: Name;X;Y (регистр неважен).
        """
        try:
            keys = {k.strip().lower(): v for k, v in row.items()}
            name = keys.get("name") or list(row.values())[0]
            x = float(keys.get("x") or list(row.values())[1])
            y = float(keys.get("y") or list(row.values())[2])
            return {"id": str(name).strip(), "x": x, "y": y}
        except Exception as e:
            print(f"Warning: Failed to parse beacon row {row}: {e}")
            return None

    # ---------- PATH ----------
    def save_path_to_file(self, positions: List[Dict[str, Any]], filename: str, session_id: str):
        """
        Пишем CSV в ./<filename>.path с заголовком X;Y
        """
        file_path = (self.base_dir / f"{filename}.path").resolve()
        with file_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["X", "Y"])
            for p in positions:
                writer.writerow([p.get("x", 0), p.get("y", 0)])
        return file_path
