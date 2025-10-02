-- Создание таблицы для хранения карт
CREATE TABLE IF NOT EXISTS maps (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для хранения маяков на картах
CREATE TABLE IF NOT EXISTS beacons (
    id SERIAL PRIMARY KEY,
    map_id INTEGER REFERENCES maps(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    x_coordinate DECIMAL(10, 2) NOT NULL,
    y_coordinate DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(map_id, name)
);

-- Создание таблицы устройств
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    mac VARCHAR(17) UNIQUE NOT NULL,
    map_id INTEGER REFERENCES maps(id) ON DELETE SET NULL,
    poll_frequency DECIMAL(5, 2) DEFAULT 1.0, -- Гц
    color VARCHAR(7) DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для измерений сигналов от маяков
CREATE TABLE IF NOT EXISTS signal_measurements (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    beacon_name VARCHAR(100) NOT NULL,
    signal_strength INTEGER NOT NULL, -- RSSI
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для вычисленных позиций
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    map_id INTEGER REFERENCES maps(id) ON DELETE CASCADE,
    x_coordinate DECIMAL(10, 2) NOT NULL,
    y_coordinate DECIMAL(10, 2) NOT NULL,
    accuracy DECIMAL(10, 2),
    algorithm VARCHAR(50) DEFAULT 'trilateration',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_beacons_map_id ON beacons(map_id);
CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac);
CREATE INDEX IF NOT EXISTS idx_devices_map_id ON devices(map_id);
CREATE INDEX IF NOT EXISTS idx_signal_measurements_device_id ON signal_measurements(device_id);
CREATE INDEX IF NOT EXISTS idx_signal_measurements_measured_at ON signal_measurements(measured_at);
CREATE INDEX IF NOT EXISTS idx_positions_device_id ON positions(device_id);
CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для обновления updated_at
CREATE TRIGGER update_maps_updated_at BEFORE UPDATE ON maps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Вставляем тестовые данные
INSERT INTO maps (name) VALUES ('office_floor_1') ON CONFLICT (name) DO NOTHING;

-- Получаем ID созданной карты
DO $$
DECLARE
    map_id_var INTEGER;
BEGIN
    SELECT id INTO map_id_var FROM maps WHERE name = 'office_floor_1';

    -- Вставляем тестовые маяки
    INSERT INTO beacons (map_id, name, x_coordinate, y_coordinate) VALUES
        (map_id_var, 'beacon_1', 3.0, -2.4),
        (map_id_var, 'beacon_2', -2.4, -0.6),
        (map_id_var, 'beacon_3', 1.8, 9.0),
        (map_id_var, 'beacon_4', -1.2, 5.5),
        (map_id_var, 'beacon_5', 4.5, 3.2),
        (map_id_var, 'beacon_6', -3.8, 7.1),
        (map_id_var, 'beacon_7', 2.2, -4.8),
        (map_id_var, 'beacon_8', -0.5, 1.3)
    ON CONFLICT (map_id, name) DO NOTHING;
END $$;

-- Вставляем тестовое устройство
INSERT INTO devices (name, mac, map_id, poll_frequency, color)
SELECT 'Test Device', '00:11:22:33:44:55', id, 1.0, '#ef4444'
FROM maps WHERE name = 'office_floor_1'
ON CONFLICT (mac) DO NOTHING;
