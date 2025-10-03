<template>
	<div class="map-wrap" :style="wrapStyle">
		<svg
			ref="svgEl"
			class="map-svg"
			:class="{ dragging }"
			:viewBox="`${vb.x} ${vb.y} ${vb.w} ${vb.h}`"
			preserveAspectRatio="xMidYMid meet"
			@wheel.prevent="onWheel"
			@dblclick.prevent="onDblClick"
			@pointerdown="onPointerDown"
			@pointermove="onPointerMove"
			@pointerup="onPointerUp"
			@pointercancel="onPointerUp"
			@pointerleave="onPointerUp"
		>
			<g :transform="contentTransform">
				<GridBackground
					:room="room"
					:gridCellSize="gridCellSize"
					:backgroundUrl="backgroundUrl"
					:viewRect="viewRectRoom"
				/>
				<BeaconsLayer
					:room="room"
					:beacons="beacons"
					:data="beaconData"
					:ring="ringOptions"
					:markerR="markerR"
					:labelDy="labelDy"
				/>
				<TrailPolyline v-if="trail?.length" :points="trail!"/>
				<DeviceMarker :pos="device" :baseR="markerR" :labelDy="labelDy"/>
			</g>
		</svg>

		<div class="toolbar">
			<button @click="zoomStep(0.9)">+</button>
			<button @click="zoomStep(1.1)">−</button>
			<button @click="fitAll">Fit</button>
			<button @click="toggleRotated">
				{{ rotated ? 'Вертикально' : 'Горизонтально' }}
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import {computed, onMounted, reactive, ref, toRefs, watch} from 'vue';
import type {Beacon, BeaconData, Point, RingOptions, Room} from './types';
import GridBackground from './base/GridBackground.vue';
import BeaconsLayer from './base/BeaconsLayer.vue';
import TrailPolyline from './base/TrailPolyline.vue';
import DeviceMarker from './base/DeviceMarker.vue';

const props = defineProps<{
	room: Room;
	beacons: Beacon[];
	beaconData?: Record<string, BeaconData>;
	device?: Point | null;
	trail?: Point[];
	backgroundUrl?: string;
	gridCellSize?: number;
	ringOptions?: RingOptions;

	viewportOffsetPx?: number;
	startRotated?: boolean;
	maxZoomOutFactor?: number;
}>();

const {room} = toRefs(props);

const markerR = 0.15;
const labelDy = 0.25;
const gridCellSize = props.gridCellSize ?? 1;

const ringOptions: RingOptions = {
	color: '#0b84f3', fillOpacity: 0.12, strokeOpacity: 0.35, min: 0, max: 0, ...props.ringOptions
};

// ---- поворот ----
const rotated = ref<boolean>(!!props.startRotated);
const toggleRotated = (): void => {
	rotated.value = !rotated.value;
};
const contentTransform = computed<string>(() =>
	rotated.value ? `translate(${room.value.h} 0) rotate(90)` : ''
);

// «мир» в текущей ориентации
const worldW = computed<number>(() => rotated.value ? room.value.h : room.value.w);
const worldH = computed<number>(() => rotated.value ? room.value.w : room.value.h);

// ---- viewBox / зум / пан ----
type VB = { x: number; y: number; w: number; h: number };
const vb = reactive<VB>({x: 0, y: 0, w: worldW.value, h: worldH.value});

const svgEl = ref<SVGSVGElement | null>(null);
const dragging = ref(false);

const fitAll = (): void => {
	vb.x = 0;
	vb.y = 0;
	vb.w = worldW.value;
	vb.h = worldH.value;
};

const clamp = (v: number, a: number, b: number): number => Math.min(Math.max(v, a), b);

const clampInWorldX = (x: number, w: number): number => {
	const min = Math.min(0, worldW.value - w);
	const max = Math.max(0, worldW.value - w);
	return clamp(x, min, max);
};
const clampInWorldY = (y: number, h: number): number => {
	const min = Math.min(0, worldH.value - h);
	const max = Math.max(0, worldH.value - h);
	return clamp(y, min, max);
};


// границы зума
const minW = computed(() => Math.min(worldW.value, worldH.value) / 20);             // макс. приближение (~20x)
const maxW = computed(() => worldW.value * (props.maxZoomOutFactor ?? 2));

const clientToWorld = (clientX: number, clientY: number) => {
	const rect = svgEl.value!.getBoundingClientRect();
	const nx = (clientX - rect.left) / rect.width;
	const ny = (clientY - rect.top) / rect.height;
	return {x: vb.x + nx * vb.w, y: vb.y + ny * vb.h};
};

const zoomAt = (clientX: number, clientY: number, factor: number): void => {
	const p = clientToWorld(clientX, clientY);

	const newW = clamp(vb.w * factor, minW.value, maxW.value);
	const newH = newW * (vb.h / vb.w); // сохраняем аспект текущего окна

	const rx = (p.x - vb.x) / vb.w;
	const ry = (p.y - vb.y) / vb.h;

	let nx = p.x - rx * newW;
	let ny = p.y - ry * newH;

	// ВАЖНО: допускать выход за 0 и за worldW/H, когда окно больше мира
	nx = clampInWorldX(nx, newW);
	ny = clampInWorldY(ny, newH);

	vb.x = nx; vb.y = ny; vb.w = newW; vb.h = newH;
};


const onWheel = (e: WheelEvent): void => {
	if (!svgEl.value) return;
	const factor = e.deltaY > 0 ? 1.1 : 0.9;
	zoomAt(e.clientX, e.clientY, factor);
};
const onDblClick = (e: MouseEvent): void => zoomAt(e.clientX, e.clientY, 0.9);

const zoomStep = (factor: number): void => {
	if (!svgEl.value) return;
	const r = svgEl.value.getBoundingClientRect();
	zoomAt(r.left + r.width / 2, r.top + r.height / 2, factor);
};

// --- pointer: pan + pinch ---
type Ptr = { id: number; x: number; y: number };
const ptrs = new Map<number, Ptr>();
let lastPinchDist = 0;

// для pan
let panStartClient = {x: 0, y: 0};
let panStartVB = {x: 0, y: 0};

const onPointerDown = (e: PointerEvent): void => {
	(e.target as Element).setPointerCapture?.(e.pointerId);
	ptrs.set(e.pointerId, {id: e.pointerId, x: e.clientX, y: e.clientY});

	if (ptrs.size === 1) {
		dragging.value = true;
		panStartClient = {x: e.clientX, y: e.clientY};
		panStartVB = {x: vb.x, y: vb.y};
	}
};

const onPointerMove = (e: PointerEvent): void => {
	if (!ptrs.has(e.pointerId)) return;
	ptrs.set(e.pointerId, {id: e.pointerId, x: e.clientX, y: e.clientY});

	// pinch-zoom
	if (ptrs.size === 2) {
		const [a, b] = [...ptrs.values()];
		if(!a || !b)
			return;
		const dx = a.x - b.x, dy = a.y - b.y;
		const dist = Math.hypot(dx, dy);
		if (lastPinchDist === 0) {
			lastPinchDist = dist;
			return;
		}
		const factor = lastPinchDist / dist;
		const cx = (a.x + b.x) / 2;
		const cy = (a.y + b.y) / 2;
		zoomAt(cx, cy, factor);
		lastPinchDist = dist;
		return;
	}

	// pan (один указатель)
	if (ptrs.size === 1 && dragging.value && svgEl.value) {
		const rect = svgEl.value.getBoundingClientRect();
		const scaleX = vb.w / rect.width;   // м/px
		const scaleY = vb.h / rect.height;  // м/px
		const dxClient = e.clientX - panStartClient.x;
		const dyClient = e.clientY - panStartClient.y;
		let nx = panStartVB.x - dxClient * scaleX;
		let ny = panStartVB.y - dyClient * scaleY;

		nx = clampInWorldX(nx, vb.w);
		ny = clampInWorldY(ny, vb.h);

		vb.x = nx; vb.y = ny;
	}
};

const onPointerUp = (e: PointerEvent): void => {
	(e.target as Element).releasePointerCapture?.(e.pointerId);
	ptrs.delete(e.pointerId);
	if (ptrs.size < 2) lastPinchDist = 0;
	if (ptrs.size === 0) dragging.value = false;
};

const viewRectRoom = computed(() => {
	if (!rotated.value) {
		return { x: vb.x, y: vb.y, w: vb.w, h: vb.h };
	}
	// transform: translate(room.h,0) rotate(90)
	return {
		x: vb.y,
		y: room.value.h - vb.x - vb.w,
		w: vb.h,
		h: vb.w,
	};
});

// при изменении ориентации/размеров — Fit
watch([rotated, () => room.value.w, () => room.value.h], () => fitAll());

// первый fit
onMounted(() => fitAll());

// стили и размеры контейнера
const wrapStyle = computed<Record<string, string>>(() => {
	const maxH = props.viewportOffsetPx != null ? `calc(100vh - ${props.viewportOffsetPx}px)` : '100vh';
	return {
		width: '100%',
		maxHeight: maxH,
		aspectRatio: `${worldW.value} / ${worldH.value}`,
		margin: '0 auto',
		background: '#fafafa'
	};
});
</script>

<style scoped>
.map-wrap {
	position: relative;
}

.map-svg {
	width: 100%;
	height: 100%;
	display: block;
	touch-action: none;
	cursor: grab;
}

.map-svg.dragging {
	cursor: grabbing;
}

.toolbar {
	position: absolute;
	right: 8px;
	top: 8px;
	display: flex;
	gap: 6px;
	background: rgba(255, 255, 255, 0.9);
	border: 1px solid #ddd;
	border-radius: 8px;
	padding: 6px 8px;
}

.toolbar button {
	padding: 4px 8px;
}
</style>
