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
    write_road BOOLEAN DEFAULT true, -- Записывать ли маршрут устройства
    color VARCHAR(7) DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Создание таблицы для отслеживания изменений устройств
CREATE TABLE IF NOT EXISTS device_changes (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    change_type VARCHAR(50) NOT NULL, -- 'map', 'freq', 'status'
    is_notified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_beacons_map_id ON beacons(map_id);
CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac);
CREATE INDEX IF NOT EXISTS idx_devices_map_id ON devices(map_id);
CREATE INDEX IF NOT EXISTS idx_positions_device_id ON positions(device_id);
CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at);
CREATE INDEX IF NOT EXISTS idx_device_changes_device_id ON device_changes(device_id);
CREATE INDEX IF NOT EXISTS idx_device_changes_is_notified ON device_changes(is_notified);

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

-- Функция для отслеживания изменений устройств
CREATE OR REPLACE FUNCTION track_device_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Проверяем изменение карты (map_id)
    IF (OLD.map_id IS DISTINCT FROM NEW.map_id) THEN
        INSERT INTO device_changes (device_id, change_type, is_notified)
        VALUES (NEW.id, 'map', false);
    END IF;

    -- Проверяем изменение частоты (poll_frequency)
    IF (OLD.poll_frequency IS DISTINCT FROM NEW.poll_frequency) THEN
        INSERT INTO device_changes (device_id, change_type, is_notified)
        VALUES (NEW.id, 'freq', false);
    END IF;

    -- Проверяем изменение статуса записи маршрута (write_road)
    IF (OLD.write_road IS DISTINCT FROM NEW.write_road) THEN
        INSERT INTO device_changes (device_id, change_type, is_notified)
        VALUES (NEW.id, 'status', false);
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для отслеживания изменений устройств
CREATE TRIGGER track_device_changes_trigger
AFTER UPDATE ON devices
FOR EACH ROW
EXECUTE FUNCTION track_device_changes();

-- Вставляем тестовые данные
-- INSERT INTO maps (name) VALUES ('yadro_nsu') ON CONFLICT (name) DO NOTHING;
INSERT INTO maps (name) VALUES ('kpa_nsu') ON CONFLICT (name) DO NOTHING;

-- Получаем ID созданных карт и вставляем маяки
DO $$
DECLARE
    -- yadro_map_id INTEGER;
    kpa_map_id INTEGER;
BEGIN
    -- SELECT id INTO yadro_map_id FROM maps WHERE name = 'yadro_nsu';
    SELECT id INTO kpa_map_id FROM maps WHERE name = 'kpa_nsu';

    -- -- Вставляем маяки для yadro_nsu
    -- INSERT INTO beacons (map_id, name, x_coordinate, y_coordinate) VALUES
    --     (yadro_map_id, 'beacon_1', 3.0, -2.4),
    --     (yadro_map_id, 'beacon_2', -2.4, -0.6),
    --     (yadro_map_id, 'beacon_3', 1.8, 9.0),
    --     (yadro_map_id, 'beacon_4', 4.8, 18.6),
    --     (yadro_map_id, 'beacon_5', -1.8, 26.4),
    --     (yadro_map_id, 'beacon_6', -1.8, 34.2),
    --     (yadro_map_id, 'beacon_7', 7.8, 34.2),
    --     (yadro_map_id, 'beacon_8', -1.8, 40.8)
    -- ON CONFLICT (map_id, name) DO NOTHING;

    -- Вставляем маяки для kpa_nsu
    INSERT INTO beacons (map_id, name, x_coordinate, y_coordinate) VALUES
        (kpa_map_id, 'beacon_1', -7.2, -4.8),
        (kpa_map_id, 'beacon_2', 3.0, -4.8),
        (kpa_map_id, 'beacon_3', 9.6, -0.6),
        (kpa_map_id, 'beacon_4', -13.8, -1.8),
        (kpa_map_id, 'beacon_5', -9.0, 4.2),
        (kpa_map_id, 'beacon_6', 6.0, 9.0),
        (kpa_map_id, 'beacon_7', -13.2, 10.8),
        (kpa_map_id, 'beacon_8', -3.0, 2.4)
    ON CONFLICT (map_id, name) DO NOTHING;
END $$;

