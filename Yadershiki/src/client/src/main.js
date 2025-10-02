import Konva from 'konva';
import './style.css';
import 'normalize.css';
import drawPoints, { drawPoint, mapCoordinates } from './points';
import PathRecord from './pathRecord';

Konva.hitOnDragEnabled = true;
const API_URL = import.meta.env.VITE_API_URL;

const record = new PathRecord();

const stage = new Konva.Stage({
	container: 'convas',
	width: window.innerWidth,
	height: window.innerHeight,
	draggable: true,
});
const origin = {x: 0, y: 0};
const center = {x: stage.width() / 2, y: stage.height() / 2};
const step = 10;

const data = await fetch(`${API_URL}/api/beacons`)
	.then((response) => {
		return response.json();
	});

const user = drawPoint(
	origin, center, step,
	{x: 0, y: 0, name: 'You', fill: 'green'}
);
const start = {x: 0, y: 0, name: 'Start', fill: 'red'};

const points = drawPoints(
	origin, center, step,
	[start, ...data]
);
	
points.add(user);
stage.add(points);


const positionSource = new EventSource(`${API_URL}/api/position`);
positionSource.onmessage = async (event) => {
	try {
		const data = await JSON.parse(event.data);
		record.add(data.x, data.y);
		const {x, y} = mapCoordinates(origin, center, step, data);

		user.x(x);
		user.y(y);

		points.batchDraw();
	} catch (err) {
		console.error(`Error: ${err}`);
	}
};

