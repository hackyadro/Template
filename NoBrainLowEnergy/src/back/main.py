from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from typing import Dict, Any
import logging
from datetime import datetime
import os

from mqtt_client import MQTTClient
from models import MessageModel, DeviceStatus, MQTTMessage
from config import settings
from routes import router, set_mqtt_client
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MQTT client instance
mqtt_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
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

    mqtt_client = MQTTClient(
        broker_host=broker_host,
        broker_port=broker_port_final,
        username=username,
        password=password,
        use_tls=use_tls,
        ca_cert_path=ca_cert_path,
        cert_file_path=cert_file_path,
        key_file_path=key_file_path
    )
    
    # Connect to MQTT broker
    await mqtt_client.connect()
    
    # Start MQTT client in background
    asyncio.create_task(mqtt_client.start())
    
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
    if debug_env is not None:
        debug_flag = debug_env.strip().lower() in ("1", "true", "yes", "on")
    else:
        debug_flag = getattr(settings, "DEBUG", False)

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
        reload=debug_flag,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )
    if debug_env is not None:
        debug_flag = debug_env.strip().lower() in ("1", "true", "yes", "on")
    else:
        debug_flag = getattr(settings, "DEBUG", False)

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
        reload=debug_flag,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )

