import json
import os
from typing import Any, Optional

# Можно переопределить путём переменной окружения STATE_FILE
STATE_FILE = os.path.abspath(os.environ.get("STATE_FILE", "state.json"))

def save_last_position(position: dict) -> None:
    """
    Атомарная запись JSON (через временный файл + rename),
    чтобы Flask не поймал «полузаписанный» файл.
    """
    tmp_path = STATE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(position, f, ensure_ascii=False)
    os.replace(tmp_path, STATE_FILE)

def load_last_position() -> Optional[dict[str, Any]]:
    """
    Безопасное чтение: если файла ещё нет или он повреждён — вернём None.
    """
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
