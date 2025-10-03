const API_PORT = import.meta.env.VITE_API_PORT || 8080;
const API_URL = `${import.meta.env.VITE_API_URL}:${API_PORT}`;



export async function fetchBeacons() {
	return await fetch(`${API_URL}/api/beacons`)
		.then((response) => {
			return response.json();
		});
}

export function openPositionSource(onmessage) {
	const source = new EventSource(`${API_URL}/api/position`);
	source.onmessage = onmessage;

	return source;
}
