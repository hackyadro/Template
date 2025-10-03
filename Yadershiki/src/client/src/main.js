import './style.css';
import 'normalize.css';
import { mapCoordinates } from './points';
import { openPositionSource } from './network';
import { drawPath, setUpStage } from './canvas';
import PathRecord from './pathRecord';

const record = new PathRecord();
let layer, path = [];
const { stage, user, getGridParams } = await setUpStage('canvas');

const positionSource = openPositionSource(async (event) => {
	try {
		const data = await JSON.parse(event.data);
		record.add(data.x, data.y);
		const { origin, center, step } = getGridParams();
		const {x, y} = mapCoordinates(origin, center, step, data);

		user.x(x);
		user.y(y);

		if (record.isRecording()) {
			path.push(x, y);
		} else {
			path = [];
		}
		layer = drawPath(stage, layer, path);

		stage.batchDraw();
	} catch (err) {
		console.error(`Error: ${err}`);
	}
});

