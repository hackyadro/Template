-- Создание таблицы клиентов (по MAC адресу)
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    mac VARCHAR(17) UNIQUE NOT NULL,
    freq INTEGER NOT NULL DEFAULT 1,
    write_road BOOLEAN NOT NULL DEFAULT true,
    map_name VARCHAR(100) NOT NULL DEFAULT 'office_floor_1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для хранения списка маяков
CREATE TABLE IF NOT EXISTS beacons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание связи между клиентами и маяками (многие ко многим)
CREATE TABLE IF NOT EXISTS client_beacons (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    beacon_id INTEGER REFERENCES beacons(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, beacon_id)
);

-- Создание таблицы для хранения данных сигналов от маяков
CREATE TABLE IF NOT EXISTS signal_measurements (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    beacon_name VARCHAR(100) NOT NULL,
    signal_strength INTEGER NOT NULL,
    map_name VARCHAR(100) NOT NULL,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для отслеживания изменений
CREATE TABLE IF NOT EXISTS client_changes (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    change_type VARCHAR(50) NOT NULL, -- 'map', 'freq', 'status'
    is_processed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_clients_mac ON clients(mac);
CREATE INDEX IF NOT EXISTS idx_signal_measurements_client_id ON signal_measurements(client_id);
CREATE INDEX IF NOT EXISTS idx_signal_measurements_measured_at ON signal_measurements(measured_at);
CREATE INDEX IF NOT EXISTS idx_client_changes_client_id ON client_changes(client_id);
CREATE INDEX IF NOT EXISTS idx_client_changes_is_processed ON client_changes(is_processed);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для обновления updated_at в таблице clients
CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Вставляем тестовые данные
INSERT INTO beacons (name) VALUES
    ('beacon_1'),
    ('beacon_2'),
    ('beacon_3'),
    ('beacon_4'),
    ('beacon_5'),
    ('beacon_6'),
    ('beacon_7'),
    ('beacon_8')
ON CONFLICT (name) DO NOTHING;

-- Вставляем тестового клиента
INSERT INTO clients (mac, freq, write_road, map_name) VALUES
    ('00:11:22:33:44:55', 1, true, 'office_floor_1')
ON CONFLICT (mac) DO NOTHING;
