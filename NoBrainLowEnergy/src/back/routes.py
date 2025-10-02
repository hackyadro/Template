from fastapi import APIRouter, HTTPException, Query, Form, WebSocket, WebSocketDisconnect
from typing import List, Optional, Annotated, Any, Dict
from datetime import datetime, timedelta
import asyncio
import json

from models import (
    SensorData, DeviceStatus, DeviceCommand, AlertMessage,
    SystemStatus, APIResponse, PaginatedResponse
)
from mqtt_client import MQTTClient

# Create router for device-related endpoints
router = APIRouter(prefix="/api/v1", tags=["devices"])

# This would be injected or passed from main app
mqtt_client: Optional[MQTTClient] = None

# WebSocket subscribers for distances streaming
_distance_subscribers: set[asyncio.Queue] = set()
# Constants shared by WebSocket info endpoints
_distance_heartbeat_interval: float = 30.0
_WS_DISTANCE_MESSAGE_SHAPE = {
    "type": "distances",
    "topic": "<topic>",
    "timestamp": "ISO8601",
    "data": {
        "names": ["..."],
        "distances": [0.0]
    },
}
# Store the main event loop to schedule coroutines from non-async threads (e.g., Paho MQTT callbacks)
_event_loop: Optional[asyncio.AbstractEventLoop] = None


async def _broadcast_distances(event: dict):
    if not _distance_subscribers:
        return
    for q in list(_distance_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            # Drop if subscriber is slow
            pass


def set_mqtt_client(client: MQTTClient):
    """Set the MQTT client instance and register distance broadcast callback."""
    global mqtt_client, _event_loop
    mqtt_client = client

    # Capture the running loop to use from MQTT (background) thread
    try:
        _event_loop = asyncio.get_running_loop()
    except RuntimeError:
        # If not in an event loop, leave as None; main may call this again later
        _event_loop = None

    # Register a catch-all callback to compute and broadcast distances
    def _on_any_message(received_msg):
        try:
            data = client.distance_model.Calc(received_msg)
            payload: Dict[str, Any] = dict(data) if isinstance(data, dict) else {"raw": data}

            beacon_positions = getattr(client, "beacon_positions", None)
            if beacon_positions:
                try:
                    estimate = client.distance_model.position_from_distances(data, beacon_positions)
                    payload["position"] = estimate
                except Exception:
                    pass

            event = {
                "type": "distances",
                "topic": received_msg.topic,
                "timestamp": received_msg.timestamp.isoformat(),
                "data": payload,
            }
            # Schedule broadcast on the main event loop even from non-async threads
            loop = _event_loop
            if loop is not None:
                asyncio.run_coroutine_threadsafe(_broadcast_distances(event), loop)
            else:
                try:
                    # Best-effort if we are in an async context
                    loop2 = asyncio.get_running_loop()
                    loop2.create_task(_broadcast_distances(event))
                except RuntimeError:
                    # No available loop; drop the event
                    pass
        except Exception:
            # Avoid breaking MQTT processing due to WS errors
            pass

    try:
        client.add_message_callback("#", _on_any_message)
    except Exception:
        # If client not ready yet, ignore; main may call this again later
        pass


def build_ws_distances_info(endpoint: str) -> dict:
    """Return metadata describing the distances WebSocket endpoint."""
    return {
        "endpoint": endpoint,
        "protocol": "websocket",
        "usage": (
            "Connect with a WebSocket client to ws://<host>:8000"
            f"{endpoint} to receive distance events."
        ),
        "message_shape": {
            "type": _WS_DISTANCE_MESSAGE_SHAPE["type"],
            "topic": _WS_DISTANCE_MESSAGE_SHAPE["topic"],
            "timestamp": _WS_DISTANCE_MESSAGE_SHAPE["timestamp"],
            "data": {
                "names": list(_WS_DISTANCE_MESSAGE_SHAPE["data"]["names"]),
                "distances": list(_WS_DISTANCE_MESSAGE_SHAPE["data"]["distances"]),
            },
        },
    }

# @router.post("/calibrate/{device_name}", response_model=APIResponse)
# async def calibrate_device(device_name: Annotated[str, Form()],
#                            beacon_name: Annotated[str, Form()]):
#     """Send command to a specific device via MQTT"""
#     if not mqtt_client or not mqtt_client.is_connected():
#         raise HTTPException(status_code=503, detail="MQTT client not connected")
#
#     try:
#         topic = f"devices/{device_name}/beacons"
#
#         return APIResponse(
#             status="OK",
#             message=f"Calibrated device {device_name}"
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to calibrate device {device_name}: {str(e)}")

# WebSocket endpoint to stream distances computed from incoming MQTT messages
@router.websocket("/ws/distances")
async def ws_distances(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _distance_subscribers.add(queue)
    try:
        # Optional greeting
        await websocket.send_json({"type": "hello", "endpoint": "distances"})
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=_distance_heartbeat_interval)
                await websocket.send_json(item)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat", "ts": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception:
        # Ignore other errors to avoid crashing endpoint
        pass
    finally:
        _distance_subscribers.discard(queue)
        try:
            await websocket.close()
        except Exception:
            pass

# Allow HTTP GET on the same path to avoid 404 when accessed via browser/HTTP
@router.api_route("/ws/distances", methods=["GET", "HEAD"], include_in_schema=False)
async def ws_distances_info() -> dict:
    return build_ws_distances_info("/api/v1/ws/distances")

# REST endpoint to return recent MQTT messages
@router.get("/mqtt/messages")
async def get_mqtt_messages(limit: int = Query(50, ge=1, le=100)):
    """Return recent MQTT messages captured by the MQTT client."""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not initialized")
    try:
        return mqtt_client.get_recent_messages(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve MQTT messages: {e}")
