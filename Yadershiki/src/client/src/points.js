import Konva from "konva";

export default function drawPoints(origin, startsAt, step, points) {
	const layer = new Konva.Layer();
	
	points.forEach((point) => {
		const x = startsAt.x + step * (point.x - origin.x);
		const y = startsAt.y + step * (point.y - origin.y);

		layer.add(drawPoint(x, y, point.fill, point.name));
	});
	
	return layer;
}

function drawPoint(x, y, fill, name) {
	const point = new Konva.Group({x, y});
	const circle = new Konva.Circle({
		radius: 10,
		fill: fill || 'gray',
		stroke: 'black',
		strokeWidth: 1,
	});

	point.add(circle);
	
	if (name !== undefined) {
		const caption = new Konva.Text({
			text: name,
			fontSize: 16,
		});

		caption.offsetX(caption.width() / 2);
		caption.offsetY(-caption.height());

		point.add(caption);
	}

	return point;
}
