from fastapi import APIRouter, HTTPException, Query, Form
from typing import List, Optional, Annotated
from datetime import datetime, timedelta

from models import (
    SensorData, DeviceStatus, DeviceCommand, AlertMessage,
    SystemStatus, APIResponse, PaginatedResponse
)
from mqtt_client import MQTTClient

# Create router for device-related endpoints
router = APIRouter(prefix="/api/v1", tags=["devices"])

# This would be injected or passed from main app
mqtt_client: Optional[MQTTClient] = None


def set_mqtt_client(client: MQTTClient):
    """Set the MQTT client instance"""
    global mqtt_client
    mqtt_client = client


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
