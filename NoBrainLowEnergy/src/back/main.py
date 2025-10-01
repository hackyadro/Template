from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from typing import Dict, Any
import logging
from datetime import datetime

from mqtt_client import MQTTClientqw
from models import MessageModel, DeviceStatus, MQTTMessage
from config import settings
from routes import router, set_mqtt_client

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
    mqtt_client = MQTTClient(
        broker_host=settings.MQTT_BROKER_HOST,
        broker_port=settings.MQTT_BROKER_PORT,
        username=settings.MQTT_USERNAME,
        password=settings.MQTT_PASSWORD,
        use_tls=settings.MQTT_USE_TLS,
        ca_cert_path=settings.MQTT_CA_CERT_PATH,
        cert_file_path=settings.MQTT_CERT_FILE_PATH,
        key_file_path=settings.MQTT_KEY_FILE_PATH
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
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
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        ssl_keyfile=settings.SSL_KEY_FILE if settings.USE_SSL else None,
        ssl_certfile=settings.SSL_CERT_FILE if settings.USE_SSL else None
    )
