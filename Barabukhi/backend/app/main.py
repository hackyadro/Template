from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import time
import json

from app.database import get_db
from app.models import (
    # Device API models (BLE devices)
    MacRequest, FreqResponse, StatusRoadResponse, MapResponse,
    PingResponse, SendSignalRequest, SendSignalResponse,
    SetMapToDeviceRequest, SetMapToDeviceResponse,
    SetFreqRequest, SetFreqResponse,
    AddMapRequest, AddMapResponse,
    # Frontend API models
    MapCreateRequest, MapResponse2, BeaconResponse, BeaconInput,
    DeviceCreateRequest, DeviceUpdateRequest, DeviceResponse,
    PositionRequest, PositionResponse, PathPoint, DevicePathResponse
)
from app.positioning import PositioningEngine, BeaconData
from app.advanced_positioning import AdvancedPositioningEngine

# Глобальный экземпляр продвинутого движка позиционирования
advanced_engine = AdvancedPositioningEngine()
engine_calibrated = False

app = FastAPI(
    title="Indoor Navigation API",
    description="REST API для indoor-навигации на основе BLE маяков",
    version="2.0.0"
)

# CORS middleware для доступа с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Indoor Navigation API",
        "version": "2.0.0",
        "endpoints": {
            "device_api": ["/get_freq", "/get_status_road", "/get_map", "/ping", "/send_signal",
                          "/set_map_to_device", "/set_freq", "/add_map"],
            "frontend_api": ["/api/maps", "/api/devices", "/api/position", "/api/path"],
            "websocket": "/ws"
        }
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Проверка здоровья API и подключения к БД"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# ==================== HELPER FUNCTIONS ====================

async def get_or_create_device(mac: str, db: AsyncSession) -> int:
    """
    Получить или создать устройство по MAC адресу.
    Возвращает device_id.
    """
    # Проверяем существование устройства
    result = await db.execute(
        text("SELECT id FROM devices WHERE mac = :mac"),
        {"mac": mac}
    )
    device = result.first()

    if device:
        return device.id

    # Создаём устройство с дефолтными настройками
    # Привязываем к дефолтной карте если она есть
    map_result = await db.execute(
        text("SELECT id FROM maps ORDER BY id LIMIT 1")
    )
    map_data = map_result.first()
    map_id = map_data.id if map_data else None

    insert_result = await db.execute(
        text("""
            INSERT INTO devices (name, mac, map_id, poll_frequency, write_road, color)
            VALUES (:name, :mac, :map_id, :poll_frequency, :write_road, :color)
            RETURNING id
        """),
        {
            "name": f"Device_{mac}",
            "mac": mac,
            "map_id": map_id,
            "poll_frequency": 1.0,
            "write_road": True,
            "color": "#3b82f6"
        }
    )
    await db.commit()
    return insert_result.scalar()


# ==================== DEVICE API (BLE устройства) ====================

@app.post("/get_freq", response_model=FreqResponse)
async def get_freq(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """Получить частоту для MAC адреса (из таблицы devices)"""
    # Автоматически создаём устройство если не существует
    await get_or_create_device(request.mac, db)

    # Получаем частоту устройства
    result = await db.execute(
        text("SELECT poll_frequency FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = result.first()

    # Конвертируем poll_frequency (Гц) в целое число
    return FreqResponse(freq=int(float(device.poll_frequency)))


@app.post("/get_status_road", response_model=StatusRoadResponse)
async def get_status_road(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """Получить статус записи маршрута для устройства"""
    # Автоматически создаём устройство если не существует
    await get_or_create_device(request.mac, db)

    # Получаем статус записи маршрута для устройства
    result = await db.execute(
        text("SELECT write_road FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = result.first()

    return StatusRoadResponse(write_road=device.write_road)


@app.post("/get_map", response_model=MapResponse)
async def get_map(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """Получить данные карты и список маяков для MAC адреса"""
    # Автоматически создаём устройство если не существует
    await get_or_create_device(request.mac, db)

    # Получаем устройство по MAC
    result = await db.execute(
        text("SELECT map_id FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = result.first()

    if not device.map_id:
        # Возвращаем дефолтную карту
        map_result = await db.execute(
            text("SELECT id, name FROM maps WHERE name = 'office_floor_1' LIMIT 1")
        )
        map_data = map_result.first()
        if not map_data:
            raise HTTPException(status_code=404, detail="Default map not found")

        map_id = map_data.id
        map_name = map_data.name
    else:
        map_id = device.map_id
        map_result = await db.execute(
            text("SELECT name FROM maps WHERE id = :map_id"),
            {"map_id": map_id}
        )
        map_data = map_result.first()
        map_name = map_data.name if map_data else "unknown"

    # Получаем список маяков для карты
    beacons_result = await db.execute(
        text("SELECT name FROM beacons WHERE map_id = :map_id ORDER BY id"),
        {"map_id": map_id}
    )
    beacons = [row.name for row in beacons_result.fetchall()]

    return MapResponse(map_name=map_name, beacons=beacons)


@app.post("/ping", response_model=PingResponse)
async def ping(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """
    Проверить наличие изменений для клиента.
    Возвращает список необработанных изменений и помечает их как отправленные.
    """
    # Автоматически создаём устройство если не существует
    device_id = await get_or_create_device(request.mac, db)

    # Получаем необработанные изменения для устройства
    changes_result = await db.execute(
        text("""
            SELECT DISTINCT change_type
            FROM device_changes
            WHERE device_id = :device_id AND is_notified = false
            ORDER BY change_type
        """),
        {"device_id": device_id}
    )
    changes = changes_result.fetchall()

    if not changes:
        return PingResponse(change=False, change_list=[])

    # Формируем список изменений
    change_list = [row.change_type for row in changes]

    # Помечаем все изменения как отправленные
    await db.execute(
        text("""
            UPDATE device_changes
            SET is_notified = true
            WHERE device_id = :device_id AND is_notified = false
        """),
        {"device_id": device_id}
    )
    await db.commit()

    return PingResponse(change=True, change_list=change_list)


@app.post("/set_map_to_device", response_model=SetMapToDeviceResponse)
async def set_map_to_device(request: SetMapToDeviceRequest, db: AsyncSession = Depends(get_db)):
    """
    Установить карту для устройства по MAC адресу.
    Создает устройство если не существует.
    """
    # Получаем или создаём карту
    map_result = await db.execute(
        text("SELECT id FROM maps WHERE name = :map_name"),
        {"map_name": request.map}
    )
    map_data = map_result.first()

    if not map_data:
        # Создаём карту если не существует
        map_insert = await db.execute(
            text("INSERT INTO maps (name) VALUES (:map_name) RETURNING id"),
            {"map_name": request.map}
        )
        map_id = map_insert.scalar()
    else:
        map_id = map_data.id

    # Получаем или создаём устройство
    device_result = await db.execute(
        text("SELECT id FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = device_result.first()

    if device:
        # Обновляем map_id для существующего устройства
        await db.execute(
            text("UPDATE devices SET map_id = :map_id WHERE mac = :mac"),
            {"map_id": map_id, "mac": request.mac}
        )
    else:
        # Создаём новое устройство с указанной картой
        await db.execute(
            text("""
                INSERT INTO devices (name, mac, map_id, poll_frequency, write_road, color)
                VALUES (:name, :mac, :map_id, :poll_frequency, :write_road, :color)
            """),
            {
                "name": f"Device_{request.mac}",
                "mac": request.mac,
                "map_id": map_id,
                "poll_frequency": 1.0,
                "write_road": True,
                "color": "#3b82f6"
            }
        )

    await db.commit()
    return SetMapToDeviceResponse(success=True)


@app.post("/set_freq", response_model=SetFreqResponse)
async def set_freq(request: SetFreqRequest, db: AsyncSession = Depends(get_db)):
    """
    Установить частоту опроса для устройства по MAC адресу.
    Создает устройство если не существует.
    """
    # Получаем или создаём устройство
    device_result = await db.execute(
        text("SELECT id FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = device_result.first()

    if device:
        # Обновляем частоту для существующего устройства
        await db.execute(
            text("UPDATE devices SET poll_frequency = :freq WHERE mac = :mac"),
            {"freq": request.freq, "mac": request.mac}
        )
    else:
        # Создаём новое устройство с указанной частотой
        # Привязываем к дефолтной карте если она есть
        map_result = await db.execute(
            text("SELECT id FROM maps ORDER BY id LIMIT 1")
        )
        map_data = map_result.first()
        map_id = map_data.id if map_data else None

        await db.execute(
            text("""
                INSERT INTO devices (name, mac, map_id, poll_frequency, write_road, color)
                VALUES (:name, :mac, :map_id, :poll_frequency, :write_road, :color)
            """),
            {
                "name": f"Device_{request.mac}",
                "mac": request.mac,
                "map_id": map_id,
                "poll_frequency": request.freq,
                "write_road": True,
                "color": "#3b82f6"
            }
        )

    await db.commit()
    return SetFreqResponse(success=True)


@app.post("/add_map", response_model=AddMapResponse)
async def add_map(request: AddMapRequest, db: AsyncSession = Depends(get_db)):
    """
    Добавить новую карту с маяками.
    Если карта уже существует, обновляет список маяков.
    """
    # Проверяем существование карты
    map_result = await db.execute(
        text("SELECT id FROM maps WHERE name = :map_name"),
        {"map_name": request.map}
    )
    map_data = map_result.first()

    if map_data:
        # Карта уже существует, используем её ID
        map_id = map_data.id

        # Удаляем старые маяки для этой карты
        await db.execute(
            text("DELETE FROM beacons WHERE map_id = :map_id"),
            {"map_id": map_id}
        )
    else:
        # Создаём новую карту
        map_insert = await db.execute(
            text("INSERT INTO maps (name) VALUES (:map_name) RETURNING id"),
            {"map_name": request.map}
        )
        map_id = map_insert.scalar()

    # Добавляем маяки
    for beacon in request.beacons:
        await db.execute(
            text("""
                INSERT INTO beacons (map_id, name, x_coordinate, y_coordinate)
                VALUES (:map_id, :name, :x, :y)
            """),
            {
                "map_id": map_id,
                "name": beacon.name,
                "x": beacon.x,
                "y": beacon.y
            }
        )

    await db.commit()
    return AddMapResponse(success=True, map_id=map_id)


@app.post("/send_signal", response_model=SendSignalResponse)
async def send_signal(request: SendSignalRequest, db: AsyncSession = Depends(get_db)):
    """
    Принять данные о сигналах от маяков и вычислить позицию.
    Новая сигнатура: name, mac, map, list:{name, signal, samples}
    """
    global engine_calibrated

    # Получаем или создаём устройство
    result = await db.execute(
        text("SELECT id, map_id, write_road FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = result.first()

    # Получаем или создаём карту
    map_result = await db.execute(
        text("SELECT id FROM maps WHERE name = :map_name"),
        {"map_name": request.map}
    )
    map_data = map_result.first()

    if not map_data:
        # Создаём карту если не существует
        map_insert = await db.execute(
            text("INSERT INTO maps (name) VALUES (:map_name) RETURNING id"),
            {"map_name": request.map}
        )
        map_id = map_insert.scalar()
    else:
        map_id = map_data.id

    if not device:
        # Создаём устройство если не существует
        device_insert = await db.execute(
            text("""
                INSERT INTO devices (name, mac, map_id, write_road)
                VALUES (:name, :mac, :map_id, :write_road)
                RETURNING id
            """),
            {"name": f"Device_{request.mac}", "mac": request.mac, "map_id": map_id, "write_road": True}
        )
        device_id = device_insert.scalar()
        write_road = True
        await db.commit()
    else:
        device_id = device.id
        write_road = device.write_road

    # Получаем последнюю позицию для использования в алгоритме как prior
    last_position_result = await db.execute(
        text("""
            SELECT x_coordinate, y_coordinate
            FROM positions
            WHERE device_id = :device_id AND map_id = :map_id
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"device_id": device_id, "map_id": map_id}
    )
    last_position = last_position_result.first()

    if last_position:
        advanced_engine.last_position = (float(last_position.x_coordinate), float(last_position.y_coordinate))

    # Получаем маяки для вычисления позиции
    beacons_result = await db.execute(
        text("""
            SELECT name, x_coordinate, y_coordinate
            FROM beacons
            WHERE map_id = :map_id
        """),
        {"map_id": map_id}
    )
    beacons_data = beacons_result.fetchall()
    beacons_map_tuples = {
        row.name: (float(row.x_coordinate), float(row.y_coordinate))
        for row in beacons_data
    }

    # Калибруем продвинутый движок при первом запросе
    if not engine_calibrated and beacons_map_tuples:
        advanced_engine.calibrate(beacons_map_tuples)
        engine_calibrated = True
        print(f"[Calibration] alpha={advanced_engine.alpha:.3f}, beta={advanced_engine.beta:.3f}")

    # Формируем данные для calculate_position_with_samples
    # report_data: {beacon_name: {'rssi': value, 'samples': count}}
    report_data = {
        signal.name: {'rssi': float(signal.signal), 'samples': signal.samples}
        for signal in request.list
    }

    # Вычисляем позицию с использованием продвинутого алгоритма с учётом samples
    position_data = advanced_engine.calculate_position_with_samples(
        report_data,
        beacons_map_tuples,
        prior_weight=0.1
    )

    # Всегда делаем commit для сохранения измерений сигналов
    if position_data:
        x, y, accuracy, algorithm = position_data

        # Сохраняем позицию только если write_road = True
        if write_road:
            await db.execute(
                text("""
                    INSERT INTO positions (device_id, map_id, x_coordinate, y_coordinate, accuracy, algorithm)
                    VALUES (:device_id, :map_id, :x, :y, :accuracy, :algorithm)
                """),
                {
                    "device_id": device_id,
                    "map_id": map_id,
                    "x": x,
                    "y": y,
                    "accuracy": accuracy,
                    "algorithm": algorithm
                }
            )

        # Broadcast позиции через WebSocket всем подключенным клиентам
        await manager.broadcast_position({
            "device_id": device_id,
            "mac": request.mac,
            "map_id": map_id,
            "x": x,
            "y": y,
            "accuracy": accuracy,
            "algorithm": algorithm,
            "timestamp": time.time()
        })

    # Commit должен быть всегда, чтобы сохранить измерения сигналов
    await db.commit()
    return SendSignalResponse(accept=True)


# ==================== WEBSOCKET API ====================

# Менеджер WebSocket соединений для broadcast позиций
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_position(self, data: dict):
        """Отправить позицию всем подключенным клиентам"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps({
                    "type": "position_update",
                    "data": data
                }))
            except Exception:
                disconnected.append(connection)

        # Удаляем отключенные соединения
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint для real-time коммуникации с фронтендом.

    Формат сообщений:
    Входящие: { "type": "get_all_device" | "get_list_map" | "write_road" | "subscribe_position", "data": {...} }
    Исходящие: { "type": "all_device" | "list_map" | "write_road" | "position_update", "data": {...} }
    """
    await manager.connect(websocket)

    try:
        while True:
            # Получаем сообщение от клиента
            raw_message = await websocket.receive_text()

            try:
                message = json.loads(raw_message)
                msg_type = message.get("type")

                # Обработка запроса get_all_device
                if msg_type == "get_all_device":
                    devices_result = await db.execute(
                        text("""
                            SELECT id, name, mac, map_id, poll_frequency, write_road, color
                            FROM devices
                            ORDER BY created_at DESC
                        """)
                    )
                    devices = devices_result.fetchall()

                    devices_list = [
                        {
                            "id": d.id,
                            "name": d.name,
                            "mac": d.mac,
                            "map_set": d.map_id,
                            "freq": float(d.poll_frequency),
                            "write_road": d.write_road,
                            "color": d.color
                        }
                        for d in devices
                    ]

                    await websocket.send_text(json.dumps({
                        "type": "all_device",
                        "data": devices_list
                    }))

                # Обработка запроса get_list_map
                elif msg_type == "get_list_map":
                    maps_result = await db.execute(
                        text("SELECT id, name, created_at FROM maps ORDER BY created_at DESC")
                    )
                    maps = maps_result.fetchall()

                    maps_list = []
                    for map_row in maps:
                        # Получаем маяки для каждой карты
                        beacons_result = await db.execute(
                            text("""
                                SELECT id, name, x_coordinate, y_coordinate
                                FROM beacons
                                WHERE map_id = :map_id
                                ORDER BY id
                            """),
                            {"map_id": map_row.id}
                        )
                        beacons = [
                            {
                                "id": b.id,
                                "name": b.name,
                                "x": float(b.x_coordinate),
                                "y": float(b.y_coordinate)
                            }
                            for b in beacons_result.fetchall()
                        ]

                        maps_list.append({
                            "id": map_row.id,
                            "name": map_row.name,
                            "beacons": beacons
                        })

                    await websocket.send_text(json.dumps({
                        "type": "list_map",
                        "data": {"maps": maps_list}
                    }))

                # Обработка add_map
                elif msg_type == "add_map":
                    data = message.get("data", {})
                    map_name = data.get("map_name")
                    beacons = data.get("beacons", [])

                    if not map_name:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"message": "map_name is required"}
                        }))
                        continue

                    # Проверяем существование карты
                    map_result = await db.execute(
                        text("SELECT id FROM maps WHERE name = :map_name"),
                        {"map_name": map_name}
                    )
                    map_data = map_result.first()

                    if map_data:
                        map_id = map_data.id
                        # Удаляем старые маяки
                        await db.execute(
                            text("DELETE FROM beacons WHERE map_id = :map_id"),
                            {"map_id": map_id}
                        )
                    else:
                        # Создаём новую карту
                        map_insert = await db.execute(
                            text("INSERT INTO maps (name) VALUES (:map_name) RETURNING id"),
                            {"map_name": map_name}
                        )
                        map_id = map_insert.scalar()

                    # Добавляем маяки
                    for beacon in beacons:
                        await db.execute(
                            text("""
                                INSERT INTO beacons (map_id, name, x_coordinate, y_coordinate)
                                VALUES (:map_id, :name, :x, :y)
                            """),
                            {
                                "map_id": map_id,
                                "name": beacon.get("name"),
                                "x": beacon.get("x"),
                                "y": beacon.get("y")
                            }
                        )

                    await db.commit()

                    # Отправляем обновлённый список карт всем клиентам
                    maps_result = await db.execute(
                        text("SELECT id, name, created_at FROM maps ORDER BY created_at DESC")
                    )
                    maps = maps_result.fetchall()

                    maps_list = []
                    for map_row in maps:
                        beacons_result = await db.execute(
                            text("""
                                SELECT id, name, x_coordinate, y_coordinate
                                FROM beacons
                                WHERE map_id = :map_id
                                ORDER BY id
                            """),
                            {"map_id": map_row.id}
                        )
                        beacons_data = [
                            {
                                "id": b.id,
                                "name": b.name,
                                "x": float(b.x_coordinate),
                                "y": float(b.y_coordinate)
                            }
                            for b in beacons_result.fetchall()
                        ]

                        maps_list.append({
                            "id": map_row.id,
                            "name": map_row.name,
                            "beacons": beacons_data
                        })

                    await websocket.send_text(json.dumps({
                        "type": "list_map",
                        "data": {"maps": maps_list}
                    }))

                # Обработка set_map_to_device
                elif msg_type == "set_map_to_device":
                    data = message.get("data", {})
                    mac = data.get("mac")
                    map_name = data.get("map_name")

                    if not mac or not map_name:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"message": "mac and map_name are required"}
                        }))
                        continue

                    # Получаем карту
                    map_result = await db.execute(
                        text("SELECT id FROM maps WHERE name = :map_name"),
                        {"map_name": map_name}
                    )
                    map_data = map_result.first()

                    if not map_data:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"message": "Map not found"}
                        }))
                        continue

                    # Обновляем устройство
                    await db.execute(
                        text("UPDATE devices SET map_id = :map_id WHERE mac = :mac"),
                        {"map_id": map_data.id, "mac": mac}
                    )
                    await db.commit()

                    # Отправляем обновлённый список устройств
                    devices_result = await db.execute(
                        text("""
                            SELECT id, name, mac, map_id, poll_frequency, write_road, color
                            FROM devices
                            ORDER BY created_at DESC
                        """)
                    )
                    devices = devices_result.fetchall()

                    devices_list = [
                        {
                            "id": d.id,
                            "name": d.name,
                            "mac": d.mac,
                            "map_set": d.map_id,
                            "freq": float(d.poll_frequency),
                            "write_road": d.write_road,
                            "color": d.color
                        }
                        for d in devices
                    ]

                    await websocket.send_text(json.dumps({
                        "type": "all_device",
                        "data": devices_list
                    }))

                # Обработка set_freq
                elif msg_type == "set_freq":
                    data = message.get("data", {})
                    mac = data.get("mac")
                    freq = data.get("freq")

                    if not mac or freq is None:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"message": "mac and freq are required"}
                        }))
                        continue

                    # Обновляем частоту устройства
                    await db.execute(
                        text("UPDATE devices SET poll_frequency = :freq WHERE mac = :mac"),
                        {"freq": float(freq), "mac": mac}
                    )
                    await db.commit()

                    # Отправляем обновлённый список устройств
                    devices_result = await db.execute(
                        text("""
                            SELECT id, name, mac, map_id, poll_frequency, write_road, color
                            FROM devices
                            ORDER BY created_at DESC
                        """)
                    )
                    devices = devices_result.fetchall()

                    devices_list = [
                        {
                            "id": d.id,
                            "name": d.name,
                            "mac": d.mac,
                            "map_set": d.map_id,
                            "freq": float(d.poll_frequency),
                            "write_road": d.write_road,
                            "color": d.color
                        }
                        for d in devices
                    ]

                    await websocket.send_text(json.dumps({
                        "type": "all_device",
                        "data": devices_list
                    }))

                # Обработка set_write_road
                elif msg_type == "set_write_road":
                    data = message.get("data", {})
                    mac = data.get("mac")
                    status = data.get("status")

                    if not mac or status is None:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {"message": "mac and status are required"}
                        }))
                        continue

                    # Обновляем статус записи для устройства
                    await db.execute(
                        text("UPDATE devices SET write_road = :status WHERE mac = :mac"),
                        {"status": bool(status), "mac": mac}
                    )
                    await db.commit()

                    # Отправляем обновлённый список устройств
                    devices_result = await db.execute(
                        text("""
                            SELECT id, name, mac, map_id, poll_frequency, write_road, color
                            FROM devices
                            ORDER BY created_at DESC
                        """)
                    )
                    devices = devices_result.fetchall()

                    devices_list = [
                        {
                            "id": d.id,
                            "name": d.name,
                            "mac": d.mac,
                            "map_set": d.map_id,
                            "freq": float(d.poll_frequency),
                            "write_road": d.write_road,
                            "color": d.color
                        }
                        for d in devices
                    ]

                    await websocket.send_text(json.dumps({
                        "type": "all_device",
                        "data": devices_list
                    }))

                # Обработка write_road (опционально - для будущего расширения)
                elif msg_type == "write_road":
                    # На данный момент просто подтверждаем получение
                    await websocket.send_text(json.dumps({
                        "type": "write_road",
                        "data": {"ok": True}
                    }))

                else:
                    # Неизвестный тип сообщения
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {"message": f"Unknown message type: {msg_type}"}
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket client disconnected")
    except Exception as e:
        manager.disconnect(websocket)
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


# ==================== FRONTEND API ====================

@app.get("/api/maps", response_model=List[MapResponse2])
async def get_maps(db: AsyncSession = Depends(get_db)):
    """Получить список всех карт с маяками"""
    result = await db.execute(text("SELECT id, name, created_at FROM maps ORDER BY created_at DESC"))
    maps = result.fetchall()

    maps_response = []
    for map_row in maps:
        # Получаем маяки для каждой карты
        beacons_result = await db.execute(
            text("""
                SELECT id, map_id, name, x_coordinate, y_coordinate, created_at
                FROM beacons
                WHERE map_id = :map_id
                ORDER BY id
            """),
            {"map_id": map_row.id}
        )
        beacons = [
            BeaconResponse(
                id=b.id,
                map_id=b.map_id,
                name=b.name,
                x_coordinate=float(b.x_coordinate),
                y_coordinate=float(b.y_coordinate),
                created_at=b.created_at
            )
            for b in beacons_result.fetchall()
        ]

        maps_response.append(
            MapResponse2(
                id=map_row.id,
                name=map_row.name,
                created_at=map_row.created_at,
                beacons=beacons
            )
        )

    return maps_response


@app.post("/api/maps", response_model=MapResponse2, status_code=201)
async def create_map(map_data: MapCreateRequest, db: AsyncSession = Depends(get_db)):
    """Создать новую карту с маяками"""
    # Создаём карту
    result = await db.execute(
        text("INSERT INTO maps (name) VALUES (:name) RETURNING id, name, created_at"),
        {"name": map_data.name}
    )
    map_row = result.first()
    map_id = map_row.id

    # Создаём маяки
    beacons = []
    for beacon in map_data.beacons:
        beacon_result = await db.execute(
            text("""
                INSERT INTO beacons (map_id, name, x_coordinate, y_coordinate)
                VALUES (:map_id, :name, :x, :y)
                RETURNING id, map_id, name, x_coordinate, y_coordinate, created_at
            """),
            {
                "map_id": map_id,
                "name": beacon.name,
                "x": beacon.x,
                "y": beacon.y
            }
        )
        b = beacon_result.first()
        beacons.append(
            BeaconResponse(
                id=b.id,
                map_id=b.map_id,
                name=b.name,
                x_coordinate=float(b.x_coordinate),
                y_coordinate=float(b.y_coordinate),
                created_at=b.created_at
            )
        )

    await db.commit()

    return MapResponse2(
        id=map_row.id,
        name=map_row.name,
        created_at=map_row.created_at,
        beacons=beacons
    )


@app.delete("/api/maps/{map_id}", status_code=204)
async def delete_map(map_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить карту"""
    result = await db.execute(
        text("DELETE FROM maps WHERE id = :map_id RETURNING id"),
        {"map_id": map_id}
    )
    await db.commit()
    if not result.first():
        raise HTTPException(status_code=404, detail="Map not found")


@app.get("/api/devices", response_model=List[DeviceResponse])
async def get_devices(db: AsyncSession = Depends(get_db)):
    """Получить список всех устройств"""
    result = await db.execute(
        text("""
            SELECT id, name, mac, map_id, poll_frequency, write_road, color, created_at, updated_at
            FROM devices
            ORDER BY created_at DESC
        """)
    )
    devices = result.fetchall()

    return [
        DeviceResponse(
            id=d.id,
            name=d.name,
            mac=d.mac,
            map_id=d.map_id,
            poll_frequency=float(d.poll_frequency),
            write_road=d.write_road,
            color=d.color,
            created_at=d.created_at,
            updated_at=d.updated_at
        )
        for d in devices
    ]


@app.post("/api/devices", response_model=DeviceResponse, status_code=201)
async def create_device(device: DeviceCreateRequest, db: AsyncSession = Depends(get_db)):
    """Создать новое устройство"""
    # Автогенерация имени если не указано
    device_name = device.name if device.name else f"Device_{device.mac}"

    result = await db.execute(
        text("""
            INSERT INTO devices (name, mac, map_id, poll_frequency, write_road, color)
            VALUES (:name, :mac, :map_id, :poll_frequency, :write_road, :color)
            RETURNING id, name, mac, map_id, poll_frequency, write_road, color, created_at, updated_at
        """),
        {
            "name": device_name,
            "mac": device.mac,
            "map_id": device.map_id,
            "poll_frequency": device.poll_frequency,
            "write_road": device.write_road,
            "color": device.color
        }
    )
    await db.commit()
    d = result.first()

    return DeviceResponse(
        id=d.id,
        name=d.name,
        mac=d.mac,
        map_id=d.map_id,
        poll_frequency=float(d.poll_frequency),
        write_road=d.write_road,
        color=d.color,
        created_at=d.created_at,
        updated_at=d.updated_at
    )


@app.patch("/api/devices/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: int, device: DeviceUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Обновить устройство (например, изменить map_id или poll_frequency)"""
    # Проверяем существование устройства
    check_result = await db.execute(
        text("SELECT id FROM devices WHERE id = :device_id"),
        {"device_id": device_id}
    )
    if not check_result.first():
        raise HTTPException(status_code=404, detail="Device not found")

    # Формируем SQL для обновления только переданных полей
    update_fields = []
    params = {"device_id": device_id}

    if device.name is not None:
        update_fields.append("name = :name")
        params["name"] = device.name

    if device.map_id is not None:
        update_fields.append("map_id = :map_id")
        params["map_id"] = device.map_id

    if device.poll_frequency is not None:
        update_fields.append("poll_frequency = :poll_frequency")
        params["poll_frequency"] = device.poll_frequency

    if device.write_road is not None:
        update_fields.append("write_road = :write_road")
        params["write_road"] = device.write_road

    if device.color is not None:
        update_fields.append("color = :color")
        params["color"] = device.color

    if not update_fields:
        # Если ничего не передано, просто возвращаем текущее устройство
        result = await db.execute(
            text("""
                SELECT id, name, mac, map_id, poll_frequency, write_road, color, created_at, updated_at
                FROM devices
                WHERE id = :device_id
            """),
            {"device_id": device_id}
        )
        d = result.first()
        return DeviceResponse(
            id=d.id,
            name=d.name,
            mac=d.mac,
            map_id=d.map_id,
            poll_frequency=float(d.poll_frequency),
            write_road=d.write_road,
            color=d.color,
            created_at=d.created_at,
            updated_at=d.updated_at
        )

    # Обновляем устройство
    update_sql = f"""
        UPDATE devices
        SET {', '.join(update_fields)}
        WHERE id = :device_id
        RETURNING id, name, mac, map_id, poll_frequency, write_road, color, created_at, updated_at
    """

    result = await db.execute(text(update_sql), params)
    await db.commit()
    d = result.first()

    return DeviceResponse(
        id=d.id,
        name=d.name,
        mac=d.mac,
        map_id=d.map_id,
        poll_frequency=float(d.poll_frequency),
        write_road=d.write_road,
        color=d.color,
        created_at=d.created_at,
        updated_at=d.updated_at
    )


@app.delete("/api/devices/{device_id}", status_code=204)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить устройство"""
    result = await db.execute(
        text("DELETE FROM devices WHERE id = :device_id RETURNING id"),
        {"device_id": device_id}
    )
    await db.commit()
    if not result.first():
        raise HTTPException(status_code=404, detail="Device not found")


@app.post("/api/position", response_model=PositionResponse)
async def get_position(request: PositionRequest, db: AsyncSession = Depends(get_db)):
    """
    Получить последнюю вычисленную позицию устройства
    Этот эндпоинт будет вызываться фронтендом для получения позиции устройства
    """
    # Получаем устройство
    device_result = await db.execute(
        text("SELECT id, map_id FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = device_result.first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Получаем карту
    map_result = await db.execute(
        text("SELECT id FROM maps WHERE name = :map_name"),
        {"map_name": request.map_name}
    )
    map_data = map_result.first()

    if not map_data:
        raise HTTPException(status_code=404, detail="Map not found")

    # Получаем последнюю позицию
    position_result = await db.execute(
        text("""
            SELECT x_coordinate, y_coordinate, accuracy, algorithm, created_at
            FROM positions
            WHERE device_id = :device_id AND map_id = :map_id
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"device_id": device.id, "map_id": map_data.id}
    )
    position = position_result.first()

    if not position:
        raise HTTPException(status_code=404, detail="No position data found for this device")

    return PositionResponse(
        x=float(position.x_coordinate),
        y=float(position.y_coordinate),
        accuracy=float(position.accuracy) if position.accuracy else None,
        algorithm=position.algorithm,
        timestamp=position.created_at
    )


@app.get("/api/path/{device_id}", response_model=DevicePathResponse)
async def get_device_path(device_id: int, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Получить историю пути устройства"""
    # Получаем устройство
    device_result = await db.execute(
        text("SELECT id, name, mac FROM devices WHERE id = :device_id"),
        {"device_id": device_id}
    )
    device = device_result.first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Получаем историю позиций
    positions_result = await db.execute(
        text("""
            SELECT x_coordinate, y_coordinate, accuracy, created_at
            FROM positions
            WHERE device_id = :device_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"device_id": device_id, "limit": limit}
    )
    positions = positions_result.fetchall()

    path = [
        PathPoint(
            x=float(p.x_coordinate),
            y=float(p.y_coordinate),
            accuracy=float(p.accuracy) if p.accuracy else None,
            timestamp=p.created_at
        )
        for p in positions
    ]

    return DevicePathResponse(
        device_id=device.id,
        device_name=device.name,
        device_mac=device.mac,
        path=path
    )
