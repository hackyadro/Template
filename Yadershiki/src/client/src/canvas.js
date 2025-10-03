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
	const step = 10;

	const getGridParams = () => ({ origin, center, step });

	const user = drawPoint(
		origin, center, step,
		{x: 0, y: 0, name: 'You', fill: 'green'}
	);
	const start = {x: 0, y: 0, name: 'Start', fill: 'red'};

	const data = await fetchBeacons();
	const points = drawPoints(
		origin, center, step,
		[start, ...data]
	);
		
	points.add(user);
	stage.add(points);

	return { stage, user, getGridParams};
}

