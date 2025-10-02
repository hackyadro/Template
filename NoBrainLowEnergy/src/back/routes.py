from fastapi import APIRouter, HTTPException, Query, Form, WebSocket, WebSocketDisconnect
from typing import List, Optional, Annotated
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
            event = {
                "type": "distances",
                "topic": received_msg.topic,
                "timestamp": received_msg.timestamp.isoformat(),
                "data": data,
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


@router.get("/devices", response_model=PaginatedResponse)
async def list_devices(
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        status: Optional[str] = Query(None, description="Filter by device status"),
        device_type: Optional[str] = Query(None, description="Filter by device type")
):
    """List all devices with pagination and filtering"""
    # Mock data - in real implementation, this would query a database
    mock_devices = [
        {
            "device_id": f"device_{i:03d}",
            "device_type": "sensor" if i % 2 == 0 else "actuator",
            "status": "online" if i % 3 != 0 else "offline",
            "last_seen": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
            "battery_level": max(0, 100 - i * 2)
        }
        for i in range(1, 51)  # 50 mock devices
    ]

    # Apply filters
    filtered_devices = mock_devices
    if status:
        filtered_devices = [d for d in filtered_devices if d["status"] == status]
    if device_type:
        filtered_devices = [d for d in filtered_devices if d["device_type"] == device_type]

    # Apply pagination
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_devices = filtered_devices[start_idx:end_idx]

    total_pages = (len(filtered_devices) + size - 1) // size

    return PaginatedResponse(
        items=paginated_devices,
        total=len(filtered_devices),
        page=page,
        size=size,
        pages=total_pages
    )


@router.get("/devices/{device_id}", response_model=DeviceStatus)
async def get_device(device_id: str):
    """Get specific device information"""
    # Mock data - in real implementation, this would query a database
    mock_device = DeviceStatus(
        device_id=device_id,
        device_type="sensor",
        status="online",
        last_seen=datetime.utcnow(),
        firmware_version="1.2.3",
        battery_level=85.5,
        uptime=3600,
        error_count=0
    )

    return mock_device


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


@router.get("/devices/{device_id}/sensor-data")
async def get_sensor_data(
        device_id: str,
        hours: int = Query(24, ge=1, le=168, description="Hours of data to retrieve"),
        sensor_type: Optional[str] = Query(None, description="Filter by sensor type")
):
    """Get sensor data for a specific device"""
    # Mock data - in real implementation, this would query a database
    mock_data = []
    base_time = datetime.utcnow()

    for i in range(hours):
        timestamp = base_time - timedelta(hours=i)
        mock_data.append({
            "sensor_id": f"{device_id}_temp",
            "sensor_type": "temperature",
            "value": 20.0 + (i % 10),
            "unit": "°C",
            "timestamp": timestamp.isoformat(),
            "battery_level": max(0, 100 - i),
            "signal_strength": -50 - (i % 20)
        })

        if sensor_type != "temperature":
            mock_data.append({
                "sensor_id": f"{device_id}_humidity",
                "sensor_type": "humidity",
                "value": 50.0 + (i % 30),
                "unit": "%",
                "timestamp": timestamp.isoformat(),
                "battery_level": max(0, 100 - i),
                "signal_strength": -50 - (i % 20)
            })

    # Apply sensor type filter
    if sensor_type:
        mock_data = [d for d in mock_data if d["sensor_type"] == sensor_type]

    return {
        "device_id": device_id,
        "data": mock_data,
        "count": len(mock_data)
    }


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status"""
    # Mock data - in real implementation, this would aggregate from database
    return SystemStatus(
        total_devices=50,
        online_devices=42,
        offline_devices=6,
        error_devices=2,
        last_update=datetime.utcnow(),
        mqtt_connected=mqtt_client.is_connected() if mqtt_client else False,
        uptime=86400  # 1 day in seconds
    )


@router.get("/alerts", response_model=List[AlertMessage])
async def get_alerts(
        severity: Optional[str] = Query(None, description="Filter by severity"),
        acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
        limit: int = Query(50, ge=1, le=100)
):
    """Get system alerts"""
    # Mock data - in real implementation, this would query a database
    mock_alerts = [
        AlertMessage(
            alert_id=f"alert_{i:03d}",
            device_id=f"device_{i % 20:03d}",
            alert_type="battery_low" if i % 3 == 0 else "sensor_error",
            severity="high" if i % 5 == 0 else "medium",
            message=f"Alert message {i}",
            timestamp=datetime.utcnow() - timedelta(minutes=i * 10),
            acknowledged=i % 4 == 0
        )
        for i in range(1, 21)
    ]

    # Apply filters
    filtered_alerts = mock_alerts
    if severity:
        filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
    if acknowledged is not None:
        filtered_alerts = [a for a in filtered_alerts if a.acknowledged == acknowledged]

    return filtered_alerts[:limit]


@router.post("/alerts/{alert_id}/acknowledge", response_model=APIResponse)
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    # In real implementation, this would update the database
    return APIResponse(
        status="success",
        message=f"Alert {alert_id} acknowledged",
        data={"alert_id": alert_id, "acknowledged_at": datetime.utcnow().isoformat()}
    )


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
