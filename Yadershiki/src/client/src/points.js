import Konva from "konva";

export default function drawPoints(origin, startsAt, step, points) {
	const layer = new Konva.Layer();
	
	points.forEach((point) => {
		layer.add(drawPoint(origin, startsAt, step, point));
	});
	
	return layer;
}

export function drawPoint(origin, startsAt, step, pointData) {
	const {x, y} = mapCoordinates(origin, startsAt, step, pointData);

	const point = new Konva.Group({x, y});
	const circle = new Konva.Circle({
		radius: 10,
		fill: pointData.fill || 'gray',
		stroke: 'black',
		strokeWidth: 1,
	});

	point.add(circle);
	
	if (pointData.name !== undefined) {
		const caption = new Konva.Text({
			text: pointData.name,
			fontSize: 16,
		});

		caption.offsetX(caption.width() / 2);
		caption.offsetY(-caption.height());

		point.add(caption);
	}

	return point;
}

export function mapCoordinates(origin, startsAt, step, coords) {
	return {
		x: startsAt.x + step * (coords.x - origin.x),
		y: startsAt.y - step * (coords.y - origin.y),
	};
}
