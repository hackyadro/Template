export default class PathRecord {
	#data = [];
	#isRecording = false;

	constructor() {
		const recordButton = document.getElementById('record');
		const downloadButton = document.getElementById('download');

		recordButton.onclick = () => {
			if (!this.isRecording()) {
				this.start();
				downloadButton.disabled = true;
				recordButton.innerHTML = 'Stop Recording';
			} else {
				this.stop();
				downloadButton.disabled = false;
				recordButton.innerHTML = 'Start Recording';
			}
		}

		downloadButton.onclick = () => {
			const blob = this.toCsv(';');
			const link = document.createElement('a');
			link.href = URL.createObjectURL(blob);
			link.download = 'recorded.path'

			document.body.appendChild(link);
			link.click();

			URL.revokeObjectURL(link.href);
			document.body.removeChild(link);
		}

		downloadButton.disabled = true;
	}

	start() {
		this.#data = [['X', 'Y']];
		this.#isRecording = true;
	}

	add(x, y) {
		if (this.#isRecording) {
			this.#data.push([x, y]);
		}
	}

	stop() {
		this.#isRecording = false;
	}

	toCsv(separator) {
		const csvContent = this.#data.map((row) => row.join(separator)).join('\n');
		const blob = new Blob([csvContent], {type: 'text/csv,charset=utf-8'});

		return blob;
	}

	isRecording() {
		return this.#isRecording;
	}
}

