import fs from 'fs';
import path from 'path';
import csv from 'csv-parser';

export default async function getBeacons(dirname) {
	const configPath = path.join(dirname, 'config.beacons');
	return new Promise((resolve, rejects) => {
		const results = [];

		fs.createReadStream(configPath)
			.pipe(csv({separator: ';'}))
			.on('data', (data) => results.push({
				name: data.Name,
				x: Number(data.X),
				y: Number(data.Y),
			}))
			.on('end', () => resolve(results))
			.on('error', () => rejects(results));
	});
}
