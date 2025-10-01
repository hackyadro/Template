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
    if sm.active_sessions:
        _, s = next(iter(sm.active_sessions.items()))
        return {"beacons": s["beacons"]}
    else:
        from app.services.config_loader import ConfigLoader
        beacons = ConfigLoader().load_beacons("standart")
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
