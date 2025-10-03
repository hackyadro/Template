<template>
	<div style="max-width: 1200px; margin:auto;">
		<h1>
			Indoor geolocation by <span style="text-decoration: underline">NoBrainLowEnergy</span>
		</h1>
		<hr style="margin: 20px;">

		<IndoorMap
			v-if="beacons.length"
			:room="room"
			:beacons="beacons"
			:beaconData="beaconData"
			:device="device"
			:trail="trail"
			:grid-cell-size="1"
			:ring-options="{ color:'#2196f3', fillOpacity:0.10, strokeOpacity:0.35, max:40 }"
		/>

		<!-- NEW: управление записью пути -->
		<div class="actions">
			<button @click="toggleRecording">
				{{ isRecording ? 'Завершить и скачать .path' : 'Начать запись пути' }}
			</button>
			<span v-if="isRecording" class="rec-dot" title="Recording"></span>
			<small v-if="recordedCount">точек: {{ recordedCount }}</small>
		</div>

		<input type="file" accept=".beacons" @change="onFile"/>
	</div>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from 'vue';
import IndoorMap from './components/IndoorMap/IndoorMap.vue';
import type {Point} from './components/IndoorMap/types';

import {normalizeToOrigin, parseBeaconsCsv} from './utils/beaconsParser';
import type {Beacon} from './utils/beaconsParser.ts';
import {ServiceWithWSBroadcast} from './services/ServiceWithWsBroadcast.ts';
import http from './services/http.ts';
import {adaptBeacons} from './utils/adaptServerPositions.ts';

const beacons = ref<Beacon[]>([]);

const pullBeacons = async () => {
	const {data} = await http.get('/beacons/config');
	const arr = adaptBeacons(data);
	const norm = normalizeToOrigin(arr);
	beacons.value = norm.beacons;
	beaconData.value = Object.fromEntries(beacons.value.map(b => [b.id, {}]));
};

const errors = ref<string[]>([]);
const beaconData = ref<Record<string, { rssi?: number; dist?: number }>>({});

onMounted(() => {
	pullBeacons();
});

const room = computed(() => {
	if (!beacons.value.length) return {w: 0, h: 0};
	const minX = Math.min(...beacons.value.map(b => b.x));
	const maxX = Math.max(...beacons.value.map(b => b.x));
	const minY = Math.min(...beacons.value.map(b => b.y));
	const maxY = Math.max(...beacons.value.map(b => b.y));
	return {w: maxX - minX || 1, h: maxY - minY || 1};
});

type UploadItem = { name: string; x: number; y: number };
type UploadResponse = {
	status?: string;
	message?: string;
	data?: { stored?: number; skipped?: Array<{ index: number; reason: unknown; name?: string }> };
};
type UploadPayload = { positions: UploadItem[] };

const pushBeaconConfig = async (beacons: Beacon[]): Promise<UploadResponse> => {
	const positions: UploadItem[] = beacons.map(b => ({name: b.id, x: +b.x, y: +b.y}));
	const payload: UploadPayload = {positions};
	const {data} = await http.post<UploadResponse>('/beacons/config', payload, {
		headers: {'Content-Type': 'application/json'},
	});
	return data;
};

const onFile = async (e: Event) => {
	const file = (e.target as HTMLInputElement).files?.[0];
	if (!file) return;
	const text = await file.text();
	const res = parseBeaconsCsv(text, {delimiter: ';', decimal: 'auto'});

	errors.value = res.errors.map(er => `Строка ${er.line}: ${er.msg} — ${er.raw}`);

	const norm = normalizeToOrigin(res.beacons);
	beacons.value = norm.beacons;

	const ok = confirm('Перезаписать текущие координаты маячков на сервере?');
	if (!ok) return;
	try {
		await pushBeaconConfig(beacons.value);
	} catch (e: any) {
		console.warn('Send error', e.message);
	}
	beaconData.value = Object.fromEntries(beacons.value.map(b => [b.id, {}]));
};

// device / trail
const device = ref<Point>({x: 5.0, y: 3.5});
const trail = ref<Point[]>([
	{x: 2.0, y: 2.0},
	{x: 3.0, y: 3.5}
]);

// ===== NEW: запись пути =====
const isRecording = ref(false);
const recorded = ref<Point[]>([]);
const recordedCount = computed(() => recorded.value.length);
const RECORD_MIN_STEP = 0.05; // м — минимальный шаг для новой точки

const dist2 = (a: Point, b: Point) => {
	const dx = a.x - b.x, dy = a.y - b.y;
	return dx * dx + dy * dy;
};

const maybeRecord = (p: Point) => {
	if (!isRecording.value) return;
	const last = recorded.value[recorded.value.length - 1];
	if (!last || dist2(last, p) >= RECORD_MIN_STEP * RECORD_MIN_STEP) {
		recorded.value.push({x: p.x, y: p.y});
		// Параллельно показываем путь на карте
		trail.value.push({x: p.x, y: p.y});
	}
};

const formatNum = (n: number) =>
	n.toLocaleString('ru-RU', {useGrouping: false, maximumFractionDigits: 6});

const savePathFile = () => {
	if (!recorded.value.length) {
		alert('Нет точек для сохранения');
		return;
	}
	const header = 'X;Y';
	const rows = recorded.value.map(p => `${formatNum(p.x)};${formatNum(p.y)}`);
	const content = [header, ...rows].join('\n');

	const blob = new Blob([content], {type: 'text/plain;charset=utf-8'});
	const ts = new Date();
	const pad = (x: number) => String(x).padStart(2, '0');
	const name = `path_${ts.getFullYear()}${pad(ts.getMonth() + 1)}${pad(ts.getDate())}_${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}.path`;

	const a = document.createElement('a');
	a.href = URL.createObjectURL(blob);
	a.download = name;
	document.body.appendChild(a);
	a.click();
	URL.revokeObjectURL(a.href);
	a.remove();
};

const toggleRecording = () => {
	if (!isRecording.value) {
		// старт записи
		recorded.value = [];
		trail.value = [];
		if (device.value) {
			recorded.value.push({...device.value});
			trail.value.push({...device.value});
		}
		isRecording.value = true;
	} else {
		// стоп + сохранение файла
		isRecording.value = false;
		savePathFile();
	}
};

// ===== /NEW =====

class EspService extends ServiceWithWSBroadcast {
	constructor(wsURL: string, logPrefix: string) {
		super(wsURL, logPrefix);
	}

	protected msgReact(event: MessageEvent<any>): void {
		const data = JSON.parse(event.data);

		switch (data.type) {
			case 'distances': {
				const data1 = data.data;
				if (data1.position) {
					const px = data1.position[0];
					const py = data1.position[1];
					device.value.x = px;
					device.value.y = py;
					// NEW: записываем точку, если идёт запись
					maybeRecord({x: px, y: py});
				}
				const distances = data1.distance as { names: string[]; distances: number[] };
				for (let i = 0; i < distances.names.length; i++) {
					const name = distances.names[i] as string;
					const value = distances.distances[i] as number;
					beaconData.value[name] = {rssi: 0, dist: value};
				}
			}
		}
	}
}

const espService: EspService = new EspService(
	`ws://192.168.137.1:8000/api/v1/ws/distances`,
	'[ESP SERVICE]: '
);

onMounted(() => {
	console.log(espService)
});
</script>

<style scoped>
.actions {
	display: flex;
	align-items: center;
	gap: 10px;
	margin: 12px 0 16px;
}

.rec-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: #e53935;
	display: inline-block;
	animation: rec-blink 1.1s infinite;
}

@keyframes rec-blink {
	50% {
		opacity: 0.2;
	}
}
</style>
