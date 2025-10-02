import asyncio

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.mqtt_config import MQTT_CONFIG
from app.services.mqtt_client import MQTTClient
from app.services.session_manager import SessionManager

app = FastAPI(title="Indoor BLE Positioning", version="0.1.0")

# CORS для фронта (MVP — открыть всем)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные синглтоны
session_manager = SessionManager()
mqtt_client = MQTTClient(session_manager)

# Роуты
app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    # сохранить loop для фоновых задач и MQTT broadcast
    loop = asyncio.get_running_loop()
    session_manager.set_loop(loop)

    # старт MQTT клиента
    mqtt_client.connect(
        host=MQTT_CONFIG["broker_host"],
        port=MQTT_CONFIG["broker_port"],
        username=MQTT_CONFIG["username"],
        password=MQTT_CONFIG["password"],
        keepalive=MQTT_CONFIG["keepalive"],
    )
    session_manager.set_mqqt_client(mqtt_client.client)
    print("Startup complete.")


@app.on_event("shutdown")
async def on_shutdown():
    mqtt_client.disconnect()
    print("Shutdown complete.")
