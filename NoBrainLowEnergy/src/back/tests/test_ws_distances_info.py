import json
import sys
from pathlib import Path

# Ensure backend package is importable without installing optional deps
BACK_DIR = Path(__file__).resolve().parents[1]
if str(BACK_DIR) not in sys.path:
    sys.path.insert(0, str(BACK_DIR))

# Fallback to stdlib json if ujson is unavailable
sys.modules.setdefault("ujson", json)

from routes import build_ws_distances_info  # noqa: E402
from main import app  # noqa: E402


def test_build_ws_distances_info_payload():
    payload = build_ws_distances_info("/ws/distances")
    assert payload["endpoint"] == "/ws/distances"
    assert payload["protocol"] == "websocket"
    assert payload["message_shape"]["type"] == "distances"


def test_ws_distances_routes_expose_get_and_head():
    route_signatures = {
        (
            getattr(route, "path", None),
            tuple(sorted(getattr(route, "methods", []))),
        )
        for route in app.routes
        if getattr(route, "methods", None)
        and getattr(route, "path", None) in {"/ws/distances", "/api/v1/ws/distances"}
    }

    assert ("/ws/distances", ("GET", "HEAD")) in route_signatures
    assert ("/api/v1/ws/distances", ("GET", "HEAD")) in route_signatures
