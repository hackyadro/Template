from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


def load_beacon_positions(path: Path) -> Dict[str, Tuple[float, float]]:
    """Load beacon coordinates from a semicolon-separated file.

    The file is expected to contain the headers ``Name;X;Y``. Additional
    columns are ignored. Rows with missing or invalid coordinates are skipped.
    """

    positions: Dict[str, Tuple[float, float]] = {}

    try:
        with path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp, delimiter=";")
            for idx, row in enumerate(reader, start=1):
                name_raw = (row.get("Name") or row.get("name") or "").strip()
                if not name_raw:
                    logger.debug("Skipping row %s in %s: empty name", idx, path)
                    continue

                x_raw = row.get("X") or row.get("x")
                y_raw = row.get("Y") or row.get("y")
                if x_raw is None or y_raw is None:
                    logger.warning(
                        "Skipping beacon '%s' in row %s of %s due to missing coordinates",
                        name_raw,
                        idx,
                        path,
                    )
                    continue

                try:
                    x = float(str(x_raw).strip())
                    y = float(str(y_raw).strip())
                except ValueError:
                    logger.warning(
                        "Skipping beacon '%s' in row %s of %s due to invalid coordinates",
                        name_raw,
                        idx,
                        path,
                    )
                    continue

                positions[name_raw] = (x, y)
    except FileNotFoundError:
        logger.warning("Beacon locations file %s not found; running without fixed anchors", path)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to load beacon locations from %s: %s", path, exc)

    return positions
