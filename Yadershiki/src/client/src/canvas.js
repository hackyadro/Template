import Konva from "konva";
import drawPoints, { drawPoint } from "./points";
import { fetchBeacons } from "./network";

export async function setUpStage(containerId) {
	Konva.hitOnDragEnabled = true;

	const stage = new Konva.Stage({
		container: containerId,
		width: window.innerWidth,
		height: window.innerHeight,
		draggable: true,
	});

	const origin = {x: 0, y: 0};
	const center = {x: stage.width() / 2, y: stage.height() / 2};
	const step = 25;

	const getGridParams = () => ({ origin, center, step });

	const user = drawPoint(
		origin, center, step,
		{x: 0, y: 0, name: 'You', fill: 'green'}
	);

	const data = await fetchBeacons();
	const points = drawPoints(
		origin, center, step,
		data
	);
		
	points.add(user);
	stage.add(points);

	return { stage, user, getGridParams};
}

export function drawPath(stage, layer, path) {
	let line;
	if (layer === undefined || layer.find('Line').length === 0) {
		layer = new Konva.Layer();
		line = new Konva.Line({
			points: [],
			stroke: 'black',
			strokeWidth: 2,
		})
		layer.add(line);
		stage.add(layer);
	} else {
		line = layer.find('Line')[0];
	}

	line.points(path);
	layer.batchDraw();
	return layer;
}
