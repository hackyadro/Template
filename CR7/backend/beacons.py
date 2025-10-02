# beacons.py
import csv
from typing import Dict, Tuple
import os
from config import BEACONS_FILE

def load_beacons_from_csv(filename: str = None) -> Dict[str, Tuple[float, float]]:
    """
    Загружает маяки из CSV (формат: Name;X;Y).
    Возвращает словарь { "beacon_1": (x, y), ... }
    """
    if filename is None:
        filename = BEACONS_FILE

    beacon_positions = {}
    try:
        if not os.path.exists(filename):
            print(f"❌ Файл маяков не найден по пути: {filename}")
            return {}

        with open(filename, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f, delimiter=';')
            header = next(csv_reader, None)

            if header and len(header) >= 3:
                print(f"Заголовок файла: {header}")

            for line_num, row in enumerate(csv_reader, 2):
                if len(row) < 3:
                    continue
                name = row[0].strip()
                try:
                    x = float(row[1].strip())
                    y = float(row[2].strip())
                    beacon_positions[name] = (x, y)
                    print(f"Загружен маяк: {name} -> ({x}, {y})")
                except ValueError:
                    print(f"Ошибка преобразования в строке {line_num}: {row}")

        print(f"✅ Загружено {len(beacon_positions)} маяков из {filename}")
        return beacon_positions

    except Exception as e:
        print(f"⚠ Ошибка при чтении {filename}: {e}")
        return {}

# Загружаем маяки при импорте модуля
BEACON_POSITIONS = load_beacons_from_csv(BEACONS_FILE)