from typing import Dict, Any, Union
from fastapi import APIRouter, Depends
from starlette.websockets import WebSocketDisconnect, WebSocket

from app.models.schemas import SessionInfo, SessionConfig, StopSessionRequest, SavePathRequest, ScannerData
from app.services.session_manager import SessionManager

router = APIRouter(prefix="/api", tags=["api"])

# Dependency (простейший DI)
def get_session_manager() -> SessionManager:
    from app.main import session_manager  # ленивый импорт, чтобы избежать циклов
    return session_manager


@router.post("/session/start")
def start_session(cfg: SessionConfig, sm: SessionManager = Depends(get_session_manager)) -> Dict[str, Any]:
    return sm.start_session(cfg.model_dump())


@router.post("/session/stop")
async def stop_session(req: StopSessionRequest, sm: SessionManager = Depends(get_session_manager)) -> Dict[str, Any]:
    return await sm.stop_session(req.sessionId)


@router.post("/path/save")
def save_path(req: SavePathRequest, sm: SessionManager = Depends(get_session_manager)) -> Dict[str, Any]:
    return sm.save_session_path(req.sessionId, req.fileName)


@router.post("/scan/data")
def scan_data(data: ScannerData, sm: SessionManager = Depends(get_session_manager)) -> Dict[str, Any]:
    return sm.process_scan_data(data.model_dump())


@router.get("/beacons")
def get_beacons(sm: SessionManager = Depends(get_session_manager)) -> Dict[str, Any]:
    # Для MVP — возвращаем текущую карту из последней активной сессии или дефолтную
    beacons = []
    if sm.active_sessions:
        # берём любую активную/последнюю
        sid, s = next(iter(sm.active_sessions.items()))
        beacons = s["beacons"]
    else:
        from app.services.config_loader import ConfigLoader
        beacons = ConfigLoader().load_beacons_from_csv("office.csv")
    return {"beacons": beacons}


@router.get("/session/{session_id}/info", response_model=Union[SessionInfo, Dict[str, Any]])
def session_info(session_id: str, sm: SessionManager = Depends(get_session_manager)):
    info = sm.get_session_info(session_id)
    return info or {"status": "error", "message": "Session not found"}


# WebSocket: /api/ws — клиент сначала шлёт {"type":"subscribe","sessionId":"..."}
@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, sm: SessionManager = Depends(get_session_manager)):
    await websocket.accept()
    session_id = None
    try:
        # ждём команду subscribe
        data = await websocket.receive_json()
        if data.get("type") != "subscribe" or "sessionId" not in data:
            await websocket.send_json({"type": "error", "message": "First message must be subscribe with sessionId"})
            await websocket.close()
            return

        session_id = data["sessionId"]
        sm.add_websocket_connection(session_id, websocket)
        await websocket.send_json({"type": "session_status", "sessionId": session_id, "status": "subscribed"})

        # держим соединение, слушаем пинги/ничего
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if session_id:
            sm.remove_websocket_connection(session_id, websocket)



@router.websocket("/ws/mock")
async def ws_mock(websocket: WebSocket, sm: SessionManager = Depends(get_session_manager)):
    """
    Мок WebSocket-эндпоинт для тестирования.
    Клиент может (опционально) отправить первым сообщением JSON:
      {
        "sessionId": "<id>",        # id сессии (по умолчанию "mock-session")
        "frequency": 1.0,           # сообщений в секунду (по умолчанию 1.0)
        "center": {"x": 0.0, "y": 0.0},  # центр генерации координат
        "radius": 5.0               # радиус распределения в тех же единицах, что и x/y
      }
    Сервер отправляет сообщения формата, совместимого с app.models.schemas.WebSocketMessage:
      {
        "type": "position_update",
        "sessionId": "...",
        "position": {"x": ..., "y": ..., "timestamp": ..., "accuracy": ...}
      }
    """
    import asyncio, json, time, math, random
    await websocket.accept()
    session_id = None
    try:
        # Попробуем прочитать начальную конфигурацию (с таймаутом)
        try:
            text = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            cfg = json.loads(text) if text else {}
        except Exception:
            cfg = {}

        session_id = cfg.get("sessionId", "mock-session")
        try:
            frequency = float(cfg.get("frequency", 1.0))
        except Exception:
            frequency = 1.0
        center = cfg.get("center", {"x": 0.0, "y": 0.0}) or {"x": 0.0, "y": 0.0}
        try:
            radius = float(cfg.get("radius", 5.0))
        except Exception:
            radius = 5.0

        # Регистрируем подключение в SessionManager => совместимость с остальной логикой проекта
        sm.add_websocket_connection(session_id, websocket)

        # Отправим статус сессии
        await websocket.send_json({
            "type": "session_status",
            "sessionId": session_id,
            "status": "running",
            "startTime": time.time()
        })

        # Параметры генерации
        interval = 1.0 / max(frequency, 0.01)

        while True:
            # генерируем случайную точку внутри круга
            ang = random.random() * 2.0 * math.pi
            r = radius * (random.random() ** 0.5)  # равномерно по площади
            x = center.get("x", 0.0) + r * math.cos(ang)
            y = center.get("y", 0.0) + r * math.sin(ang)
            pos = {
                "x": round(x, 6),
                "y": round(y, 6),
                "timestamp": time.time(),
                "accuracy": round(random.uniform(0.3, 3.0), 3)
            }
            message = {
                "type": "position_update",
                "sessionId": session_id,
                "position": pos
            }
            await websocket.send_json(message)
            await asyncio.sleep(interval)

    except Exception as e:
        # Если возможно — отправим ошибку клиенту
        try:
            await websocket.send_json({"type": "error", "sessionId": session_id, "message": str(e)})
        except Exception:
            pass
    finally:
        if session_id:
            sm.remove_websocket_connection(session_id, websocket)

