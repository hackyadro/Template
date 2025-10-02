import dotenv from 'dotenv';
import express from 'express';
import path from 'path';
import compression from 'compression';
import bodyParser from 'body-parser';
import cors from 'cors';
import { fileURLToPath } from 'url';
import mqtt from 'mqtt';

dotenv.config();
const port = process.env.PORT;
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


const app = express();
app.use(compression());
app.use(cors());
app.use(bodyParser.json());

let clients = [];
let state = [];

console.log('=== Server starting ===');
console.log('Endpoints registered: /, /beacons, /api/state, /api/status');

// Вместо localhost используем переменную окружения
const mqttHost = process.env.MQTT_HOST || 'localhost';
const mqttPort = process.env.MQTT_PORT || 1883;

const mqttClient = mqtt.connect(`mqtt://${mqttHost}:${mqttPort}`, {
    reconnectPeriod: 5000,
    connectTimeout: 10000
});

mqttClient.on('connect', () => {
    console.log('✅ Подключились к MQTT');
    
    // Подписываемся на все топики skynet
    mqttClient.subscribe('skynet/#', (err) => {
        if (err) {
            console.log('❌ Ошибка подписки:', err);
        } else {
            console.log('✅ Подписались на skynet/#');
        }
    });
});

// Убедитесь что этот обработчик есть и работает:
mqttClient.on('message', (topic, message) => {
    console.log(`🔔 MQTT ПОЛУЧЕНО: [${topic}]`, message.toString());
    
    try {
        const data = JSON.parse(message.toString());
        console.log('📊 Данные из MQTT:', data);
        
        // ВАЖНО: обновляем state данными из MQTT
        state = data.data || data; // берем либо data.data, либо весь объект
        console.log('🔄 State обновлен:', state);
        
        // Уведомляем SSE клиентов
        notifyClients();
        console.log('📢 Клиенты уведомлены');
        
    } catch (e) {
        console.log('❌ Ошибка парсинга:', e.message);
        // Если ошибка парсинга, сохраняем как текст
        state = [{ error: 'parse_error', message: message.toString() }];
        notifyClients();
    }
});

mqttClient.on('error', (err) => {
    console.log('❌ MQTT ошибка:', err.message);
});

app.get('/', (req, res) => {
	res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/beacons', (req, res) => {
    const headers = {
        'Content-Type': 'text/event-stream',
        'Access-Control-Allow-Origin': '*',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    };
    res.writeHead(200, headers);

    const clientId = genUniqueId();
    const newClient = {
        id: clientId,
        res,
    };

    clients.push(newClient);

    console.log(`${clientId} - Connection opened. Total clients: ${clients.length}`);

    // Отправляем текущее состояние сразу при подключении
    const initialData = `data: ${JSON.stringify(state)}\n\n`;
    res.write(initialData);
    res.flush();

    req.on('close', () => {
        console.log(`${clientId} - Connection closed. Total clients: ${clients.length}`);
        clients = clients.filter(client => client.id !== clientId);
    });

    req.on('error', (err) => {
        console.log(`${clientId} - Connection error:`, err.message);
        clients = clients.filter(client => client.id !== clientId);
    });
});

function genUniqueId(){
	return Date.now() + '-' + Math.floor(Math.random() * 1000000000);
}

function notifyClients() {
    const sendData = `data: ${JSON.stringify(state)}\n\n`;
    const disconnectedClients = [];

    clients.forEach((client, index) => {
        try {
            client.res.write(sendData);
            client.res.flush();
        } catch (err) {
            console.log(`❌ Ошибка отправки клиенту ${client.id}:`, err.message);
            disconnectedClients.push(index);
        }
    });

    // Удаляем отключившихся клиентов
    if (disconnectedClients.length > 0) {
        clients = clients.filter((_, index) => !disconnectedClients.includes(index));
        console.log(`🗑️ Удалено ${disconnectedClients.length} отключившихся клиентов`);
    }
}


// Получить текущее состояние (разово)
app.get('/api/state', (req, res) => {
    res.json({
        state: state,
        clientsCount: clients.length,
        timestamp: new Date().toISOString()
    });
});

// Получить последние MQTT сообщения
app.get('/api/messages', (req, res) => {
    res.json({
        state: state,
        message: 'Это текущее состояние из MQTT',
        timestamp: new Date().toISOString()
    });
});

// Получить статус сервера
app.get('/api/status', (req, res) => {
    res.json({
        service: 'Main Server',
        status: 'running',
        clients: clients.length,
        mqtt_connected: mqttClient ? mqttClient.connected : false,
        timestamp: new Date().toISOString()
    });
});

// Получить информацию о MQTT
app.get('/api/mqtt-info', (req, res) => {
    res.json({
        connected: mqttClient ? mqttClient.connected : false,
        topics: ['skynet/data', 'skynet/events', 'skynet/test'],
        timestamp: new Date().toISOString()
    });
});

// Тестовый endpoint для проверки работы
app.post('/api/test-mqtt', (req, res) => {
    const testData = req.body;
    
    console.log('🧪 Тестовые данные:', testData);
    
    // Принудительно обновляем state
    state = testData;
    notifyClients();
    
    res.json({ 
        success: true, 
        message: 'Данные принудительно обновлены',
        state: state 
    });
});

app.post('/api/simulate-mqtt', (req, res) => {
    const testData = req.body;
    
    // Имитируем получение MQTT сообщения
    const mockMessage = JSON.stringify(testData);
    mqttClient.emit('message', 'skynet/test', mockMessage);
    
    res.json({ 
        success: true, 
        message: 'MQTT сообщение сымитировано',
        data: testData
    });
});

// Простой ping
app.get('/api/ping', (req, res) => {
    res.json({ status: 'ok', time: new Date().toISOString() });
});

app.listen(port, () => {
    console.log(`Starting server on ${port}`);
});