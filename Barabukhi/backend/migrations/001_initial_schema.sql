-- Создание таблицы для хранения информации о beacon-маяках
CREATE TABLE IF NOT EXISTS beacons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    x_coordinate DECIMAL(10, 2) NOT NULL,
    y_coordinate DECIMAL(10, 2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для хранения измерений RSSI
CREATE TABLE IF NOT EXISTS rssi_measurements (
    id SERIAL PRIMARY KEY,
    beacon_id INTEGER REFERENCES beacons(id) ON DELETE CASCADE,
    rssi_value INTEGER NOT NULL,
    distance DECIMAL(10, 2),
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для хранения вычисленных позиций
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    x_coordinate DECIMAL(10, 2) NOT NULL,
    y_coordinate DECIMAL(10, 2) NOT NULL,
    accuracy DECIMAL(10, 2),
    algorithm VARCHAR(50) DEFAULT 'trilateration',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для хранения траекторий движения
CREATE TABLE IF NOT EXISTS trajectories (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    position_id INTEGER REFERENCES positions(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_rssi_beacon_id ON rssi_measurements(beacon_id);
CREATE INDEX IF NOT EXISTS idx_rssi_measured_at ON rssi_measurements(measured_at);
CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at);
CREATE INDEX IF NOT EXISTS idx_trajectories_session_id ON trajectories(session_id);
CREATE INDEX IF NOT EXISTS idx_trajectories_created_at ON trajectories(created_at);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для обновления updated_at в таблице beacons
CREATE TRIGGER update_beacons_updated_at BEFORE UPDATE ON beacons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
