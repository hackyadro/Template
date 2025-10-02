import Konva from 'konva';
import './style.css';
import 'normalize.css';
import drawPoints from './points';

Konva.hitOnDragEnabled = true;

let stage = new Konva.Stage({
	container: 'convas',
	width: window.innerWidth,
	height: window.innerHeight,
	draggable: true,
});

const markers = [
	{x: 0, y: 0, name: 'Start'},
	{x: 12, y: 45, fill: 'red'},
	{x: -7, y: 19, fill: 'red'},
	{x: 5, y: -10, fill: 'red'}
];

const points = drawPoints(
	{x: 0, y: 0},
	{x: stage.width() / 2, y: stage.height() / 2},
	10,
	markers
);

stage.add(points);
