-- Добавление базовых координат для устройств
ALTER TABLE devices ADD COLUMN IF NOT EXISTS base_x DECIMAL(10, 2) DEFAULT 0.0;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS base_y DECIMAL(10, 2) DEFAULT 0.0;

-- Обновляем существующие записи
UPDATE devices SET base_x = 0.0, base_y = 0.0 WHERE base_x IS NULL OR base_y IS NULL;
