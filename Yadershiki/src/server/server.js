import dotenv from 'dotenv';
import express from 'express';
import path from 'path';
import compression from 'compression';
import bodyParser from 'body-parser';
import cors from 'cors';
import { fileURLToPath } from 'url';

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

	const sendData = `data: ${JSON.stringify(state)}\n\n`;

	res.write(sendData);
	res.flush();

	const clientId = genUniqueId();
	const newClient = {
		id: clientId,
		res,
	};

	clients.push(newClient);

	console.log(`${clientId} - Connection opened`);

	req.on('close', () => {
		console.log(`${clientId} - Connection closed`);
		clients = clients.filter(client => client.id !== clientId);
	});
});

function genUniqueId(){
	return Date.now() + '-' + Math.floor(Math.random() * 1000000000);
}

function notifyClients() {
	const sendData = `data: ${JSON.stringify(state)}\n\n`;

	for (let i = 0; i < clients.length; i++) {
		clients[i].res.write(sendData);
		clients[i].res.flush();
	}
}

app.listen(port, () => {
	console.log(`Starting server on ${port}`);
});
