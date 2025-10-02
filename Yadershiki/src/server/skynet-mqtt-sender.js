import express from 'express';
import mqtt from 'mqtt';

const app = express();
const PORT = 8085;

app.use(express.json());

// Подключаемся к EMQX (который в Docker)
// В MQTT болванке добавьте таймауты и реконнект
// Тоже используем переменные окружения
const mqttHost = process.env.MQTT_HOST || 'localhost'; 
const mqttPort = process.env.MQTT_PORT || 1883;

const mqttClient = mqtt.connect(`mqtt://${mqttHost}:${mqttPort}`, {
    reconnectPeriod: 5000,
    connectTimeout: 10000
});

let mqttReady = false;

mqttClient.on('connect', () => {
    console.log('✅ MQTT болванка подключена к брокеру');
    mqttReady = true;
});

mqttClient.on('error', (err) => {
    console.log('❌ Ошибка MQTT:', err.message);
    mqttReady = false;
});

mqttClient.on('close', () => {
    console.log('🔌 MQTT соединение закрыто');
    mqttReady = false;
});


// Главная страница
app.get('/', (req, res) => {
    res.json({
        service: 'MQTT Sender (Node.js)',
        status: 'running',
        mqtt_connected: mqttClient.connected,
        endpoints: [
            'POST /send-data',
            'POST /send-event', 
            'GET /status'
        ]
    });
});

// Статус подключения
app.get('/status', (req, res) => {
    res.json({
        mqtt_connected: mqttClient.connected,
        timestamp: new Date().toISOString()
    });
});

// Отправка данных
app.post('/send-data', (req, res) => {
    const data = req.body;
    
    // Отправляем в формате который ожидает основной сервер
    const message = data; // отправляем как есть, без обертки
    
    mqttClient.publish('skynet/data', JSON.stringify(message));
    console.log('📤 Отправлены RAW данные:', message);
    
    res.json({ success: true, message: 'Данные отправлены' });
});

// Отправка событий
app.post('/send-event', (req, res) => {
    if (!mqttClient.connected) {
        return res.status(500).json({ error: 'MQTT не подключен' });
    }

    const { event, details } = req.body;
    
    const message = {
        type: 'event',
        event: event || 'unknown',
        details: details || {},
        timestamp: new Date().toISOString(),
        from: 'mqtt-sender'
    };
    
    mqttClient.publish('skynet/events', JSON.stringify(message));
    console.log('📤 Отправлено событие:', event);
    
    res.json({ 
        success: true, 
        message: 'Событие отправлено через MQTT',
        sent: message
    });
});

// Автоматическая отправка тестовых данных
app.post('/test', (req, res) => {
    if (!mqttClient.connected) {
        return res.status(500).json({ error: 'MQTT не подключен' });
    }

    const testData = {
        type: 'test',
        value: Math.random() * 100,
        timestamp: new Date().toISOString(),
        from: 'mqtt-sender'
    };
    
    mqttClient.publish('skynet/test', JSON.stringify(testData));
    console.log('📤 Отправлен тест:', testData.value);
    
    res.json({ 
        success: true, 
        message: 'Тестовое сообщение отправлено',
        sent: testData
    });
});
process.on('SIGINT', () => {
    console.log('🛑 Получен SIGINT. Завершаем работу...');
    
    // Закрываем MQTT соединение
    if (mqttClient) {
        mqttClient.end();
    }
    
    // Закрываем HTTP сервер
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('🛑 Получен SIGTERM. Завершаем работу...');
    
    if (mqttClient) {
        mqttClient.end();
    }
    
    process.exit(0);
});
// Запуск сервера
app.listen(PORT, () => {
    console.log(`🚀 MQTT болванка запущена на http://localhost:${PORT}`);
    console.log(`📡 Подключается к MQTT брокеру: localhost:1883`);
});

