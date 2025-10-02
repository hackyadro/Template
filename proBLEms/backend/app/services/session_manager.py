import uuid
import time
import json
import asyncio
import threading
from typing import Dict, List, Any, Optional

from fastapi import WebSocket
import paho.mqtt.client as mqtt

from app.mqtt_config import MQTT_CONFIG
from app.services.positioning import PositioningService, Kalman2D
from app.services.config_loader import ConfigLoader


class SessionManager:
    """
    Держит активную сессию, ее позиции, WebSocket-подключения.
    Потокобезопасно: MQTT callbacks могут приходить из другого потока (paho-mqtt).
    Для отправки в WS используем event loop FastAPI.
    """

    def __init__(self, loop: Optional[
            asyncio.AbstractEventLoop] = None):
        self.mqtt_client = None
        self.active_session: Dict[str, Any] = {}
        self.websocket_connections: List[WebSocket] = []
        self.positioning = PositioningService()
        self.config_loader = ConfigLoader()
        self.loop = loop  # event loop FastAPI
        self._lock = threading.RLock()

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def set_mqqt_client(self, mqqt_client: mqtt.Client):
        self.mqqt_client = mqqt_client

    def start_session(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Создаёт новую сессию отслеживания"""
        if self.active_session:
            return {
                "sessionId": None,
                "status": "error",
                "message": f"Session already started"
            }

        session_id = str(uuid.uuid4())
        try:
            beacons = self.config_loader.load_beacons_from_csv(
                "standart.beacons")
            with self._lock:
                self.active_session = {
                    "id": session_id,
                    "config": config,
                    "beacons": beacons,
                    "positions": [],
                    "last_reading": [],
                    "start_time": time.time(),
                    "status": "active",
                    "kf": Kalman2D(),  # фильтр на сессию
                }
            period_ms = int(1000 / float(config["frequency"]))
            print(period_ms)
            self.publish_scan_duration(period_ms)
            return {
                "sessionId": session_id,
                "status": "started",
                "beacons_loaded": len(beacons),
                "message": f"Session started with "
                           f"{config.get('frequency', 5.0)}Hz frequency",
            }
        except Exception as e:
            return {
                "sessionId": None,
                "status": "error",
                "message": f"Failed to start session: {e}"
            }

    def publish_scan_duration(self, duration):
        if not self.mqqt_client.is_connected():
            return
        try:
            self.mqqt_client.publish(MQTT_CONFIG["topic_config"], duration)
        except Exception as e:
            print(f"[MQTT] publish error: {e}")

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Останавливает сессию, закрывает WS"""
        with self._lock:
            session = self.active_session.copy()
            conns = self.websocket_connections.copy()
            self.active_session.clear()
            self.websocket_connections.clear()
        if not session:
            return {"status": "error", "message": "Session not found"}

        session["status"] = "stopped"
        session["end_time"] = time.time()

        for ws in conns:
            try:
                await ws.close()
            except Exception:
                pass

        duration = session["end_time"] - session["start_time"]
        return {
            "status": "stopped",
            "sessionId": session_id,
            "points_count": len(session["positions"]),
            "duration_seconds": round(duration, 2)
        }

    def process_scan_data(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает данные от сканера, вычисляет позицию и рассылает WS"""
        if not self.active_session:
            return {"status": "processed"}

        try:
            pos = self.positioning.calculate_position(
                readings=[r for r in scan_data["beaconReadings"]],
                beacons=self.active_session["beacons"],
            )
            ts = scan_data.get("timestamp", time.time())

            # сгладим
            x_sm, y_sm = self.active_session["kf"].update(pos["x"], pos["y"])
            position = {"x": x_sm, "y": y_sm,
                        "accuracy": pos.get("accuracy", None), "timestamp": ts}

            with self._lock:
                self.active_session["positions"].append(position)
                self.active_session["last_reading"] = \
                    scan_data["beaconReadings"]

            # WS broadcast — через event loop
            msg = {
                "type": "position_update",
                "sessionId": self.active_session["id"],
                "position": position
            }
            if self.loop and not self.loop.is_closed():
                asyncio.run_coroutine_threadsafe(self._broadcast(msg),
                                                 self.loop)

            return {
                "status": "processed",
                "position": position,
                "session_points": len(self.active_session["positions"])
            }

        except Exception as e:
            return {"status": "error",
                    "message": f"Position calculation failed: {e}"}

    # def save_session_path(self, session_id: str, filename: str) -> Dict[str, Any]:
    #     """Сохраняет маршрут сессии в файл"""
    #     with self._lock:
    #         session = self.active_sessions.get(session_id)
    #     if not session:
    #         return {"status": "error", "message": "Session not found"}
    #
    #     try:
    #         file_path = self.config_loader.save_path_to_file(session["positions"], filename, session_id)
    #         return {"status": "saved", "file_path": str(file_path), "points_count": len(session["positions"])}
    #     except Exception as e:
    #         return {"status": "error", "message": f"Failed to save path: {e}"}

    # def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
    #     with self._lock:
    #         session = self.active_sessions.get(session_id)
    #     if not session:
    #         return None
    #     return {
    #         "sessionId": session_id,
    #         "status": session["status"],
    #         "startTime": session["start_time"],
    #         "pointsCount": len(session["positions"]),
    #         "beaconsCount": len(session["beacons"]),
    #     }

    def add_websocket_connection(self, session_id: str, websocket: WebSocket):
        with self._lock:
            self.websocket_connections.append(websocket)

    def remove_websocket_connection(self, websocket: WebSocket):
        with self._lock:
            try:
                self.websocket_connections.remove(websocket)
            except ValueError:
                pass

    async def _broadcast(self, message: Dict[str, Any]):
        """Асинхронная рассылка в WebSocket всем подписанным клиентам"""
        payload = json.dumps(message, ensure_ascii=False)

        dead = []
        for ws in self.websocket_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            for ws in dead:
                self.remove_websocket_connection(ws)
