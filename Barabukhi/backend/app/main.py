from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import time

from app.database import get_db
from app.models import (
    # Device API models (BLE devices)
    MacRequest, FreqResponse, StatusRoadResponse, MapResponse,
    PingResponse, SendSignalRequest, SendSignalResponse,
    # Frontend API models
    MapCreateRequest, MapResponse2, BeaconResponse,
    DeviceCreateRequest, DeviceUpdateRequest, DeviceResponse,
    PositionRequest, PositionResponse, PathPoint, DevicePathResponse
)
from app.positioning import PositioningEngine, BeaconData

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
            "device_api": ["/get_freq", "/get_status_road", "/get_map", "/ping", "/send_signal"],
            "frontend_api": ["/api/maps", "/api/devices", "/api/position", "/api/path"]
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
        # Нет изменений
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"Ping processed in {elapsed_ms:.2f} ms (no changes)")
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


@app.post("/send_signal", response_model=SendSignalResponse)
async def send_signal(request: SendSignalRequest, db: AsyncSession = Depends(get_db)):
    """
    Принять данные о сигналах от маяков и вычислить позицию
    """
    # Получаем или создаём устройство
    result = await db.execute(
        text("SELECT id, map_id, write_road FROM devices WHERE mac = :mac"),
        {"mac": request.mac}
    )
    device = result.first()

    if not device:
        # Создаём устройство если не существует
        map_result = await db.execute(
            text("SELECT id FROM maps WHERE name = :map_name"),
            {"map_name": request.map_name}
        )
        map_data = map_result.first()

        if not map_data:
            # Создаём карту если не существует
            map_insert = await db.execute(
                text("INSERT INTO maps (name) VALUES (:map_name) RETURNING id"),
                {"map_name": request.map_name}
            )
            map_id = map_insert.scalar()
        else:
            map_id = map_data.id

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
        map_id = device.map_id
        write_road = device.write_road

    # Сохраняем измерения сигналов
    for signal in request.list:
        await db.execute(
            text("""
                INSERT INTO signal_measurements (device_id, beacon_name, signal_strength)
                VALUES (:device_id, :beacon_name, :signal_strength)
            """),
            {
                "device_id": device_id,
                "beacon_name": signal.name,
                "signal_strength": signal.signal
            }
        )

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
    beacons_map = {
        row.name: BeaconData(row.name, float(row.x_coordinate), float(row.y_coordinate))
        for row in beacons_data
    }

    # Вычисляем позицию
    signals = [(signal.name, signal.signal) for signal in request.list]
    position_data = PositioningEngine.calculate_position(signals, beacons_map)

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

    await db.commit()
    return SendSignalResponse(accept=True)


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
    result = await db.execute(
        text("""
            INSERT INTO devices (name, mac, map_id, poll_frequency, write_road, color)
            VALUES (:name, :mac, :map_id, :poll_frequency, :write_road, :color)
            RETURNING id, name, mac, map_id, poll_frequency, write_road, color, created_at, updated_at
        """),
        {
            "name": device.name,
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
