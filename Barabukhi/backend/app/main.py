from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.models import (
    MacRequest, FreqResponse, StatusRoadResponse, MapResponse,
    PingResponse, SendSignalRequest, SendSignalResponse
)

app = FastAPI(
    title="Indoor Navigation API",
    description="REST API для indoor-навигации на основе BLE маяков",
    version="1.0.0"
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
        "version": "1.0.0",
        "endpoints": [
            "/get_freq",
            "/get_status_road",
            "/get_map",
            "/ping",
            "/send_signal"
        ]
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Проверка здоровья API и подключения к БД"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# ==================== CLIENT API ====================

@app.post("/get_freq", response_model=FreqResponse)
async def get_freq(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """
    Получить частоту для MAC адреса.
    """
    # Получаем данные клиента из БД по MAC адресу
    result = await db.execute(
        text("SELECT freq FROM clients WHERE mac = :mac"),
        {"mac": request.mac}
    )
    client = result.first()

    if not client:
        # Если клиент не найден, создаём его с дефолтными значениями
        await db.execute(
            text("""
                INSERT INTO clients (mac, freq, write_road, map_name)
                VALUES (:mac, 1, true, 'office_floor_1')
            """),
            {"mac": request.mac}
        )
        await db.commit()
        return FreqResponse(freq=1)

    return FreqResponse(freq=client.freq)


@app.post("/get_status_road", response_model=StatusRoadResponse)
async def get_status_road(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """
    Получить статус записи маршрута для MAC адреса.
    """
    # Получаем данные клиента из БД по MAC адресу
    result = await db.execute(
        text("SELECT write_road FROM clients WHERE mac = :mac"),
        {"mac": request.mac}
    )
    client = result.first()

    if not client:
        # Если клиент не найден, создаём его с дефолтными значениями
        await db.execute(
            text("""
                INSERT INTO clients (mac, freq, write_road, map_name)
                VALUES (:mac, 1, true, 'office_floor_1')
            """),
            {"mac": request.mac}
        )
        await db.commit()
        return StatusRoadResponse(write_road=True)

    return StatusRoadResponse(write_road=client.write_road)


@app.post("/get_map", response_model=MapResponse)
async def get_map(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """
    Получить данные карты и список маяков для MAC адреса.
    """
    # Получаем данные клиента из БД по MAC адресу
    result = await db.execute(
        text("SELECT id, map_name FROM clients WHERE mac = :mac"),
        {"mac": request.mac}
    )
    client = result.first()

    if not client:
        # Если клиент не найден, создаём его с дефолтными значениями
        await db.execute(
            text("""
                INSERT INTO clients (mac, freq, write_road, map_name)
                VALUES (:mac, 1, true, 'office_floor_1')
            """),
            {"mac": request.mac}
        )
        await db.commit()

        # Получаем все маяки
        beacons_result = await db.execute(text("SELECT name FROM beacons ORDER BY id"))
        beacons = [row.name for row in beacons_result.fetchall()]

        return MapResponse(map_name='office_floor_1', beacons=beacons)

    # Получаем маяки для клиента (если назначены конкретные)
    beacons_result = await db.execute(
        text("""
            SELECT b.name
            FROM beacons b
            JOIN client_beacons cb ON b.id = cb.beacon_id
            WHERE cb.client_id = :client_id
            ORDER BY b.id
        """),
        {"client_id": client.id}
    )
    beacons = [row.name for row in beacons_result.fetchall()]

    # Если у клиента нет назначенных маяков, возвращаем все
    if not beacons:
        beacons_result = await db.execute(text("SELECT name FROM beacons ORDER BY id"))
        beacons = [row.name for row in beacons_result.fetchall()]

    return MapResponse(map_name=client.map_name, beacons=beacons)


@app.post("/ping", response_model=PingResponse)
async def ping(request: MacRequest, db: AsyncSession = Depends(get_db)):
    """
    Проверить наличие изменений для клиента.
    """
    # Получаем клиента
    result = await db.execute(
        text("SELECT id FROM clients WHERE mac = :mac"),
        {"mac": request.mac}
    )
    client = result.first()

    if not client:
        # Если клиент не найден, создаём его
        await db.execute(
            text("""
                INSERT INTO clients (mac, freq, write_road, map_name)
                VALUES (:mac, 1, true, 'office_floor_1')
            """),
            {"mac": request.mac}
        )
        await db.commit()
        return PingResponse(change=False, change_list=[])

    # Проверяем наличие необработанных изменений
    changes_result = await db.execute(
        text("""
            SELECT change_type
            FROM client_changes
            WHERE client_id = :client_id AND is_processed = false
        """),
        {"client_id": client.id}
    )
    changes = changes_result.fetchall()

    if not changes:
        return PingResponse(change=False, change_list=[])

    # Формируем список изменений
    change_list = [row.change_type for row in changes]

    # Помечаем изменения как обработанные
    await db.execute(
        text("""
            UPDATE client_changes
            SET is_processed = true
            WHERE client_id = :client_id AND is_processed = false
        """),
        {"client_id": client.id}
    )
    await db.commit()

    return PingResponse(change=True, change_list=change_list)


@app.post("/send_signal", response_model=SendSignalResponse)
async def send_signal(request: SendSignalRequest, db: AsyncSession = Depends(get_db)):
    """
    Принять данные о сигналах от маяков.
    """
    # Получаем или создаём клиента
    result = await db.execute(
        text("SELECT id FROM clients WHERE mac = :mac"),
        {"mac": request.mac}
    )
    client = result.first()

    if not client:
        # Создаём нового клиента
        result = await db.execute(
            text("""
                INSERT INTO clients (mac, freq, write_road, map_name)
                VALUES (:mac, 1, true, :map_name)
                RETURNING id
            """),
            {"mac": request.mac, "map_name": request.map_name}
        )
        await db.commit()
        client_id = result.scalar()
    else:
        client_id = client.id

    # Сохраняем измерения сигналов
    for signal_data in request.list:
        await db.execute(
            text("""
                INSERT INTO signal_measurements (client_id, beacon_name, signal_strength, map_name)
                VALUES (:client_id, :beacon_name, :signal_strength, :map_name)
            """),
            {
                "client_id": client_id,
                "beacon_name": signal_data.name,
                "signal_strength": signal_data.signal,
                "map_name": request.map_name
            }
        )

    await db.commit()

    return SendSignalResponse(accept=True)
