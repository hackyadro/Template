-- Создание таблицы для хранения сессий записи маршрута
CREATE TABLE IF NOT EXISTS road_sessions (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(device_id, name)
);

-- Добавление внешнего ключа к таблице positions для связи с road_sessions
ALTER TABLE positions ADD COLUMN IF NOT EXISTS road_session_id INTEGER REFERENCES road_sessions(id) ON DELETE SET NULL;

-- Индекс для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_road_sessions_device_id ON road_sessions(device_id);
CREATE INDEX IF NOT EXISTS idx_road_sessions_is_active ON road_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_positions_road_session_id ON positions(road_session_id);

-- Добавление поля для хранения текущей активной сессии в devices
ALTER TABLE devices ADD COLUMN IF NOT EXISTS current_road_session_id INTEGER REFERENCES road_sessions(id) ON DELETE SET NULL;
