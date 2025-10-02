from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from app.database import get_db
from app.models import (
    Beacon, BeaconCreate,
    RSSIMeasurement, RSSIMeasurementCreate,
    Position, PositionCreate, PositionRequest, PositionResponse,
    Trajectory, TrajectoryCreate
)
from app.positioning import PositioningEngine

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
        "endpoints": {
            "beacons": "/beacons",
            "positions": "/positions",
            "trajectories": "/trajectories"
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


# ==================== BEACONS ====================

@app.get("/beacons", response_model=List[Beacon])
async def get_beacons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех маяков"""
    result = await db.execute(
        text("SELECT * FROM beacons ORDER BY id LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip}
    )
    beacons = result.mappings().all()
    return [Beacon(**dict(beacon)) for beacon in beacons]


@app.get("/beacons/{beacon_id}", response_model=Beacon)
async def get_beacon(beacon_id: int, db: AsyncSession = Depends(get_db)):
    """Получить информацию о конкретном маяке"""
    result = await db.execute(
        text("SELECT * FROM beacons WHERE id = :beacon_id"),
        {"beacon_id": beacon_id}
    )
    beacon = result.mappings().first()
    if not beacon:
        raise HTTPException(status_code=404, detail="Beacon not found")
    return Beacon(**dict(beacon))


@app.post("/beacons", response_model=Beacon, status_code=201)
async def create_beacon(beacon: BeaconCreate, db: AsyncSession = Depends(get_db)):
    """Создать новый маяк"""
    try:
        result = await db.execute(
            text("""
                INSERT INTO beacons (name, x_coordinate, y_coordinate, description)
                VALUES (:name, :x_coordinate, :y_coordinate, :description)
                RETURNING *
            """),
            {
                "name": beacon.name,
                "x_coordinate": beacon.x_coordinate,
                "y_coordinate": beacon.y_coordinate,
                "description": beacon.description
            }
        )
        await db.commit()
        created_beacon = result.mappings().first()
        return Beacon(**dict(created_beacon))
    except Exception as e:
        await db.rollback()
        if "unique" in str(e).lower():
            raise HTTPException(status_code=400, detail=f"Beacon with name '{beacon.name}' already exists")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/beacons/{beacon_id}", status_code=204)
async def delete_beacon(beacon_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить маяк"""
    result = await db.execute(
        text("DELETE FROM beacons WHERE id = :beacon_id RETURNING id"),
        {"beacon_id": beacon_id}
    )
    await db.commit()
    if not result.first():
        raise HTTPException(status_code=404, detail="Beacon not found")


# ==================== RSSI MEASUREMENTS ====================

@app.post("/measurements", response_model=RSSIMeasurement, status_code=201)
async def create_measurement(measurement: RSSIMeasurementCreate, db: AsyncSession = Depends(get_db)):
    """Создать новое RSSI измерение"""
    # Вычисляем расстояние из RSSI
    distance = PositioningEngine.rssi_to_distance(measurement.rssi_value)

    result = await db.execute(
        text("""
            INSERT INTO rssi_measurements (beacon_id, rssi_value, distance)
            VALUES (:beacon_id, :rssi_value, :distance)
            RETURNING *
        """),
        {
            "beacon_id": measurement.beacon_id,
            "rssi_value": measurement.rssi_value,
            "distance": distance
        }
    )
    await db.commit()
    created_measurement = result.mappings().first()
    return RSSIMeasurement(**dict(created_measurement))


@app.get("/measurements", response_model=List[RSSIMeasurement])
async def get_measurements(
    beacon_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Получить список RSSI измерений"""
    if beacon_id:
        query = text("""
            SELECT * FROM rssi_measurements
            WHERE beacon_id = :beacon_id
            ORDER BY measured_at DESC
            LIMIT :limit OFFSET :skip
        """)
        result = await db.execute(query, {"beacon_id": beacon_id, "limit": limit, "skip": skip})
    else:
        query = text("""
            SELECT * FROM rssi_measurements
            ORDER BY measured_at DESC
            LIMIT :limit OFFSET :skip
        """)
        result = await db.execute(query, {"limit": limit, "skip": skip})

    measurements = result.mappings().all()
    return [RSSIMeasurement(**dict(m)) for m in measurements]


# ==================== POSITIONS ====================

@app.post("/positions/calculate", response_model=PositionResponse)
async def calculate_position(request: PositionRequest, db: AsyncSession = Depends(get_db)):
    """
    Вычислить позицию на основе RSSI измерений от маяков.
    Опционально сохранить в траекторию.
    """
    # Получаем все маяки
    beacons_result = await db.execute(text("SELECT * FROM beacons"))
    beacons_data = beacons_result.mappings().all()
    beacons = [Beacon(**dict(b)) for b in beacons_data]

    # Вычисляем позицию
    position_data = PositioningEngine.calculate_position(request.measurements, beacons)

    if not position_data:
        raise HTTPException(status_code=400, detail="Could not calculate position from provided measurements")

    x, y, accuracy, algorithm = position_data

    # Сохраняем позицию
    result = await db.execute(
        text("""
            INSERT INTO positions (x_coordinate, y_coordinate, accuracy, algorithm)
            VALUES (:x, :y, :accuracy, :algorithm)
            RETURNING *
        """),
        {"x": x, "y": y, "accuracy": accuracy, "algorithm": algorithm}
    )
    await db.commit()
    position = Position(**dict(result.mappings().first()))

    # Сохраняем измерения
    for measurement in request.measurements:
        distance = PositioningEngine.rssi_to_distance(measurement.rssi_value)
        await db.execute(
            text("""
                INSERT INTO rssi_measurements (beacon_id, rssi_value, distance)
                VALUES (:beacon_id, :rssi_value, :distance)
            """),
            {
                "beacon_id": measurement.beacon_id,
                "rssi_value": measurement.rssi_value,
                "distance": distance
            }
        )
    await db.commit()

    trajectory_id = None

    # Сохраняем в траекторию если требуется
    if request.save_trajectory:
        session_id = request.session_id or uuid4()

        # Получаем следующий номер в последовательности для этой сессии
        seq_result = await db.execute(
            text("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                FROM trajectories
                WHERE session_id = :session_id
            """),
            {"session_id": str(session_id)}
        )
        next_seq = seq_result.scalar()

        trajectory_result = await db.execute(
            text("""
                INSERT INTO trajectories (session_id, position_id, sequence_number)
                VALUES (:session_id, :position_id, :sequence_number)
                RETURNING id
            """),
            {
                "session_id": str(session_id),
                "position_id": position.id,
                "sequence_number": next_seq
            }
        )
        await db.commit()
        trajectory_id = trajectory_result.scalar()

    return PositionResponse(position=position, trajectory_id=trajectory_id)


@app.get("/positions", response_model=List[Position])
async def get_positions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Получить список вычисленных позиций"""
    result = await db.execute(
        text("""
            SELECT * FROM positions
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip}
    )
    positions = result.mappings().all()
    return [Position(**dict(p)) for p in positions]


# ==================== TRAJECTORIES ====================

@app.get("/trajectories/{session_id}", response_model=List[dict])
async def get_trajectory(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Получить траекторию движения для конкретной сессии"""
    result = await db.execute(
        text("""
            SELECT
                t.id as trajectory_id,
                t.session_id,
                t.sequence_number,
                t.created_at as trajectory_created_at,
                p.id as position_id,
                p.x_coordinate,
                p.y_coordinate,
                p.accuracy,
                p.algorithm,
                p.created_at as position_created_at
            FROM trajectories t
            JOIN positions p ON t.position_id = p.id
            WHERE t.session_id = :session_id
            ORDER BY t.sequence_number ASC
        """),
        {"session_id": str(session_id)}
    )
    trajectory_points = result.mappings().all()

    if not trajectory_points:
        raise HTTPException(status_code=404, detail="Trajectory not found")

    return [
        {
            "trajectory_id": point["trajectory_id"],
            "session_id": point["session_id"],
            "sequence_number": point["sequence_number"],
            "position": {
                "id": point["position_id"],
                "x_coordinate": float(point["x_coordinate"]),
                "y_coordinate": float(point["y_coordinate"]),
                "accuracy": float(point["accuracy"]) if point["accuracy"] else None,
                "algorithm": point["algorithm"],
                "created_at": point["position_created_at"]
            },
            "created_at": point["trajectory_created_at"]
        }
        for point in trajectory_points
    ]


@app.get("/trajectories")
async def get_all_trajectories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех уникальных сессий траекторий"""
    result = await db.execute(
        text("""
            SELECT
                session_id,
                COUNT(*) as points_count,
                MIN(created_at) as start_time,
                MAX(created_at) as end_time
            FROM trajectories
            GROUP BY session_id
            ORDER BY start_time DESC
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip}
    )
    sessions = result.mappings().all()
    return [dict(session) for session in sessions]
