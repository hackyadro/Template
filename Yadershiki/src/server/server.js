import dotenv from 'dotenv';
import express from 'express';
import path from 'path';
import compression from 'compression';
import bodyParser from 'body-parser';
import cors from 'cors';
import { fileURLToPath } from 'url';
import mqtt from 'mqtt';
import getBeacons from './beacons.js';
import { createTracker } from './locationcals.js'; // исправлен импорт

// Добавить эту функцию (или удалить её вызовы)
async function improvedTrilaterate(dirname, rssi) {
    console.log('Legacy trilateration called with:', rssi);
    return { x: 0, y: 0, error: 'legacy_method' };
}
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
let tracker;

console.log('Server starting');
console.log('Endpoints registered: /, /beacons, /api/state, /api/status');

const mqttHost = process.env.MQTT_HOST || 'localhost';
const mqttPort = process.env.MQTT_PORT || 1883;

const mqttClient = mqtt.connect(`mqtt://${mqttHost}:${mqttPort}`, {
    reconnectPeriod: 5000,
    connectTimeout: 10000
});

const mqttTopics = ['skynet/#', 'beacons/rssi'];


async function initializeTracker() {
    try {
        tracker = await createTracker(".");
        console.log('Beacon tracker initialized');
        
        tracker.on('position', ({ position, usedBeacons, timestamp }) => {
            console.log('New position:', position);
            state = position;
            notifyClients();
        });
        
        tracker.on('error', (error) => {
            console.error('Tracker error:', error);
        });
        
    } catch (error) {
        console.error('Failed to initialize tracker:', error);
    }
}

mqttClient.on('connect', () => {
    console.log('Connected to MQTT');
    
    mqttTopics.forEach((topic) => {
        mqttClient.subscribe(topic, (err) => {
            if (err) {
                console.log(`Could not subscribe ${topic}`);
            } else {
                console.log(`Subscribed on ${topic}`);
            }
        });
    });
});

mqttClient.on('message', async (topic, message) => {
    console.log(`MQTT received: [${topic}]`, message.toString());
    
    try {
        const data = JSON.parse(message.toString());
        console.log('Got data:', data);
        
        if (topic === 'beacons/rssi') {
            if (tracker) {
                tracker.addRSSIData(data);
                console.log('Data sent to tracker');
            } else {
                console.log('Tracker not initialized yet, using legacy method');
                const rssi = data.data || data;
                state = await improvedTrilaterate(__dirname, rssi);
                notifyClients();
            }
        } else {
            const rssi = data.data || data;
            state = await improvedTrilaterate(__dirname, rssi);
            notifyClients();
        }
        
        console.log('Updated state:', state);
        
    } catch (e) {
        console.log('Parsing error:', e.message);
        state = { error: 'parse_error', message: message.toString() };
        notifyClients();
    }
});

mqttClient.on('error', (err) => {
    console.log('MQTT error:', err.message);
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.get('/api/position', (req, res) => {
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
    return Date.now() + '-' + Math.floor(Math.random() * 1_000_000_000);
}

function notifyClients() {
    const sendData = `data: ${JSON.stringify(state)}\n\n`;
    const disconnectedClients = [];

    clients.forEach((client, index) => {
        try {
            client.res.write(sendData);
            client.res.flush();
        } catch (err) {
            console.log(`Error sending to ${client.id}:`, err.message);
            disconnectedClients.push(index);
        }
    });

    if (disconnectedClients.length > 0) {
        clients = clients.filter((_, index) => !disconnectedClients.includes(index));
        console.log(`Disconnected ${disconnectedClients.length} clients`);
    }
}

app.get('/api/beacons', async (req, res) => {
    const beacons = await getBeacons(__dirname);
    res.json(beacons);
});

app.get('/api/state', (req, res) => {
    res.json({
        state: state,
        clientsCount: clients.length,
        timestamp: new Date().toISOString()
    });
});

app.get('/api/tracker-status', (req, res) => {
    const bufferStatus = tracker ? tracker.getBufferStatus() : {};
    
    res.json({
        trackerInitialized: !!tracker,
        bufferStatus: bufferStatus,
        clientsCount: clients.length,
        timestamp: new Date().toISOString()
    });
});

app.get('/api/messages', (req, res) => {
    res.json({
        state: state,
        message: 'Current MQTT state',
        timestamp: new Date().toISOString()
    });
});

app.get('/api/status', (req, res) => {
    res.json({
        service: 'Main Server',
        status: 'running',
        clients: clients.length,
        mqtt_connected: mqttClient ? mqttClient.connected : false,
        tracker_initialized: !!tracker,
        timestamp: new Date().toISOString()
    });
});

app.get('/api/mqtt-info', (req, res) => {
    res.json({
        connected: mqttClient ? mqttClient.connected : false,
        topics: mqttTopics,
        timestamp: new Date().toISOString()
    });
});

app.post('/api/test-mqtt', (req, res) => {
    const testData = req.body;
    
    console.log('Тестовые данные:', testData);
    
    state = testData;
    notifyClients();
    
    res.json({ 
        success: true, 
        message: 'Данные принудительно обновлены',
        state: state 
    });
});

app.post('/api/simulate-beacons', (req, res) => {
    const testData = req.body;
    
    if (tracker) {
        tracker.addRSSIData(testData);
        res.json({ 
            success: true, 
            message: 'Данные маяков отправлены в трекер',
            data: testData
        });
    } else {
        res.status(500).json({ 
            success: false, 
            message: 'Трекер не инициализирован'
        });
    }
});

app.post('/api/simulate-mqtt', (req, res) => {
    const testData = req.body;
    
    const mockMessage = JSON.stringify(testData);
    mqttClient.emit('message', 'skynet/test', mockMessage);
    
    res.json({ 
        success: true, 
        message: 'MQTT сообщение сымитировано',
        data: testData
    });
});

app.get('/api/ping', (req, res) => {
    res.json({ status: 'ok', time: new Date().toISOString() });
});

// Запускаем сервер после инициализации
async function startServer() {
    await initializeTracker();
    
    app.listen(port, () => {
        console.log(`Server started on port ${port}`);
    });
}

startServer().catch(console.error);