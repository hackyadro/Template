from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from typing import Dict, Any
from pathlib import Path
import logging
from datetime import datetime
import os
import sys

from beacon_loader import load_beacon_positions
from mqtt_client import MQTTClient
from models import MessageModel, DeviceStatus, MQTTMessage
from routes import router, set_mqtt_client, build_ws_distances_info
import routes as routes_module
from fastapi.responses import JSONResponse, RedirectResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MQTT client instance
mqtt_client = None
SEARCH_ROOT = Path(__file__).resolve().parent
BEACON_FILE_PATH = SEARCH_ROOT / "cfg" / "locations.beacons"



@asynccontextmanager
async def lifespan(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],  # empty list = no origins allowed
        allow_credentials=False,
        allow_methods=[],
        allow_headers=[],
    )

    """Manage application lifecycle"""
    global mqtt_client
    
    # Startup
    logger.info("Starting FastAPI application with MQTT integration")

    def _env_int(name: str, default: int) -> int:
        v = os.getenv(name)
        try:
            return int(v) if v is not None else default
        except ValueError:
            logger.warning(f"Invalid int for {name}: {v}, using default {default}")
            return default

    broker_host = os.getenv("MQTT_BROKER_HOST", "localhost")
    broker_port = _env_int("MQTT_BROKER_PORT", 1883)
    broker_port_safe = _env_int("MQTT_BROKER_PORT_SAFE", 8883)

    use_tls_env = os.getenv("MQTT_USE_TLS")
    if use_tls_env is not None:
        use_tls = use_tls_env.strip().lower() in ("1", "true", "yes", "on")
    else:
        cert_file = os.getenv("MQTT_CERT_FILE_PATH")
        key_file = os.getenv("MQTT_KEY_FILE_PATH")
        use_tls = bool(cert_file and key_file)

    broker_port_final = broker_port_safe if use_tls else broker_port

    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")

    ca_cert_path = os.getenv("MQTT_CA_CERT_PATH")
    cert_file_path = os.getenv("MQTT_CERT_FILE_PATH")
    key_file_path = os.getenv("MQTT_KEY_FILE_PATH")

    logger.info(
        f"MQTT config - host: {broker_host}, port: {broker_port_final}, use_tls: {use_tls}, username: {'set' if username else 'unset'}"
    )

    beacon_positions = load_beacon_positions(BEACON_FILE_PATH)
    app.state.beacon_positions = beacon_positions
    app.state.beacon_config_path = BEACON_FILE_PATH
    if beacon_positions:
        logger.info("Loaded %d beacon locations from %s", len(beacon_positions), BEACON_FILE_PATH)
    else:
        logger.warning("No beacon locations loaded from %s", BEACON_FILE_PATH)

    mqtt_client = MQTTClient(
        broker_host=broker_host,
        broker_port=broker_port_final,
        username=username,
        password=password,
        use_tls=use_tls,
        ca_cert_path=ca_cert_path,
        cert_file_path=cert_file_path,
        key_file_path=key_file_path,
        beacon_positions=beacon_positions,
    )
    
    # Connect to MQTT broker
    await mqtt_client.connect()
    
    # Start MQTT client network loop in background
    asyncio.create_task(mqtt_client.start())

    # Wait for the MQTT connection to be fully established before subscribing
    wait_timeout = float(os.getenv("MQTT_CONNECT_WAIT_TIMEOUT", "10"))
    waited = 0.0
    interval = 0.1
    while not mqtt_client.is_connected() and waited < wait_timeout:
        await asyncio.sleep(interval)
        waited += interval

    if not mqtt_client.is_connected():
        logger.warning("MQTT connection not established within timeout; skipping auto-subscribe for now.")
    else:
        # Auto-subscribe to topics from environment variable
        auto_subscribe_topics = os.getenv("MQTT_AUTO_SUBSCRIBE_TOPICS", "")
        if auto_subscribe_topics:
            topics = [t.strip() for t in auto_subscribe_topics.split(",") if t.strip()]
            for topic in topics:
                try:
                    await mqtt_client.subscribe(topic)
                    logger.info(f"Auto-subscribed to topic: {topic}")
                except Exception as e:
                    logger.error(f"Failed to auto-subscribe to {topic}: {e}")
    
    # Set MQTT client for routes
    set_mqtt_client(mqtt_client)
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application")
    if mqtt_client:
        await mqtt_client.disconnect()

# Create FastAPI app with lifespan management
app = FastAPI(
    title="NoBrainLowEnergy API",
    description="FastAPI backend server with MQTT broker integration",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router)

# WebSocket endpoint without API prefix that streams only distances list
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/distance")
async def ws_distance(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    routes_module._distance_subscribers.add(queue)
    try:
        while True:
            item = await queue.get()  # Wait for next distance event; no heartbeat/greeting
            try:
                data = item.get("data") if isinstance(item, dict) else None
                distances = data.get("distances") if isinstance(data, dict) else None
                if distances is not None:
                    await websocket.send_json(distances)
            except Exception:
                # Silently skip malformed events
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        routes_module._distance_subscribers.discard(queue)
        try:
            await websocket.close()
        except Exception:
            pass

# WebSocket endpoint without API prefix that streams full distance events
@app.websocket("/ws/distances")
async def ws_distances(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    routes_module._distance_subscribers.add(queue)
    try:
        # Optional greeting
        await websocket.send_json({"type": "hello", "endpoint": "distances"})
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=routes_module._distance_heartbeat_interval)
                await websocket.send_json(item)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat", "ts": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        routes_module._distance_subscribers.discard(queue)
        try:
            await websocket.close()
        except Exception:
            pass

# HTTP GET/HEAD endpoint for /ws/distances to provide info
@app.api_route("/ws/distances", methods=["GET", "HEAD"], include_in_schema=False)
async def ws_distances_info():
    return build_ws_distances_info("/ws/distances")

# Backward-compat redirect: support /devices → /api/v1/devices
@app.get("/devices")
async def redirect_devices(request: Request):
    query = request.url.query
    target = "/api/v1/devices"
    if query:
        target = f"{target}?{query}"
    return RedirectResponse(url=target, status_code=307)

# Set MQTT client for routes
if mqtt_client:
    set_mqtt_client(mqtt_client)

# Read allowed origins from env (comma-separated) with sensible defaults
_allowed = os.getenv("ALLOWED_ORIGINS")
if _allowed:
    allowed_origins = [s.strip() for s in _allowed.split(",") if s.strip()]
else:
    allowed_origins = ["http://localhost:3000", "http://localhost:8080"]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "NoBrainLowEnergy API Server",
        "timestamp": datetime.utcnow().isoformat(),
        "mqtt_connected": mqtt_client.is_connected() if mqtt_client else False
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mqtt_status": "connected" if mqtt_client and mqtt_client.is_connected() else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/mqtt/publish")
async def publish_message(message: MQTTMessage):
    """Publish a message to MQTT broker"""
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT client not connected")
    
    try:
        await mqtt_client.publish(message.topic, message.payload, message.qos, message.retain)
        return {
            "status": "success",
            "message": "Message published successfully",
            "topic": message.topic
        }
    except Exception as e:
        logger.error(f"Failed to publish message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish message: {str(e)}")

@app.post("/mqtt/subscribe")
async def subscribe_to_topic(topic: str):
    """Subscribe to an MQTT topic"""
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT client not connected")
    
    try:
        await mqtt_client.subscribe(topic)
        return {
            "status": "success",
            "message": f"Subscribed to topic: {topic}",
            "topic": topic
        }
    except Exception as e:
        logger.error(f"Failed to subscribe to topic: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")

@app.get("/mqtt/messages")
async def get_recent_messages(limit: int = 10):
    """Get recent MQTT messages"""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT client not available")
    
    messages = mqtt_client.get_recent_messages(limit)
    return {
        "messages": messages,
        "count": len(messages)
    }

@app.get("/devices/status")
async def get_device_status():
    """Get status of connected devices"""
    # This would typically fetch from a database or cache
    # For now, return mock data
    return {
        "devices": [
            {
                "device_id": "sensor_001",
                "status": "online",
                "last_seen": datetime.utcnow().isoformat(),
                "battery_level": 85
            }
        ]
    }

if __name__ == "__main__":
    # Read server run configuration directly from environment
    api_host = os.getenv("API_HOST", "0.0.0.0")
    try:
        api_port = int(os.getenv("API_PORT", "8000"))
    except ValueError:
        api_port = 8000

    debug_env = os.getenv("DEBUG", None)

    # FastAPI TLS logic (independent)
    fastapi_tls_env = os.getenv("FASTAPI_TLS_ON", None)
    if fastapi_tls_env is not None:
        fastapi_tls_on = fastapi_tls_env.strip().lower() in ("1", "true", "yes", "on")
    else:
        fastapi_tls_on = False

    ssl_keyfile = os.getenv("SSL_KEY_FILE", None) if fastapi_tls_on else None
    ssl_certfile = os.getenv("SSL_CERT_FILE", None) if fastapi_tls_on else None

    if fastapi_tls_on:
        if not ssl_keyfile or not ssl_certfile:
            print("ERROR: FASTAPI_TLS_ON is enabled but SSL_KEY_FILE or SSL_CERT_FILE is not set.")
            print("Set both SSL_KEY_FILE and SSL_CERT_FILE environment variables.")
            import sys
            sys.exit(1)

    uvicorn.run(
        "main:app",
        host=api_host,
        port=api_port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )

    # FastAPI TLS logic (independent)
    fastapi_tls_env = os.getenv("FASTAPI_TLS_ON", None)
    if fastapi_tls_env is not None:
        fastapi_tls_on = fastapi_tls_env.strip().lower() in ("1", "true", "yes", "on")
    else:
        fastapi_tls_on = False

    ssl_keyfile = os.getenv("SSL_KEY_FILE", None) if fastapi_tls_on else None
    ssl_certfile = os.getenv("SSL_CERT_FILE", None) if fastapi_tls_on else None

    if fastapi_tls_on:
        if not ssl_keyfile or not ssl_certfile:
            print("ERROR: FASTAPI_TLS_ON is enabled but SSL_KEY_FILE or SSL_CERT_FILE is not set.")
            print("Set both SSL_KEY_FILE and SSL_CERT_FILE environment variables.")
            import sys
            sys.exit(1)

    uvicorn.run(
        "main:app",
        host=api_host,
        port=api_port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )

