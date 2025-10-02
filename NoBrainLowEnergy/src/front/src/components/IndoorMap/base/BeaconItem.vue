<template>
	<g class="beacon-item">
		<circle
			v-if="radius != null"
			:cx="beacon.x" :cy="beacon.y" :r="radius"
			:fill="ringColor" :fill-opacity="fillOpacity"
			:stroke="ringColor" :stroke-opacity="strokeOpacity"
			stroke-width="0.05" vector-effect="non-scaling-stroke"
		/>
		<circle :cx="beacon.x" :cy="beacon.y" :r="markerR" fill="#0b84f3" opacity="0.9"/>

		<SmartLabel
			:x="beacon.x"
			:y="beacon.y - labelDy"
			:text="labelText"
			:room="room"
			:pad="0.1"
			anchor="middle"
		/>
	</g>
</template>

<script setup lang="ts">
import {computed} from 'vue';
import SmartLabel from './SmartLabel.vue';
import type {Beacon, BeaconData, RingOptions, Room} from '../types';

const props = defineProps<{
	beacon: Beacon;
	room: Room;              // НУЖЕН для проверки границ
	data?: BeaconData;       // { rssi?, dist? }
	ring?: RingOptions;
	markerR?: number; labelDy?: number;
}>();

const markerR = computed(() => props.markerR ?? 0.15);
const labelDy = computed(() => props.labelDy ?? 0.25);

// круг по dist
const ringColor = computed(() => props.ring?.color ?? '#0b84f3');
const fillOpacity = computed(() => props.ring?.fillOpacity ?? 0.12);
const strokeOpacity = computed(() => props.ring?.strokeOpacity ?? 0.35);
const minR = computed(() => props.ring?.min ?? 0);
const maxR = computed(() => props.ring?.max ?? 0);

const radius = computed<number | null>(() => {
	const d = props.data?.dist;
	if (typeof d !== 'number' || d <= 0 || !isFinite(d)) return null;
	let r = d;
	if (minR.value > 0) r = Math.max(r, minR.value);
	if (maxR.value > 0) r = Math.min(r, maxR.value);
	return r;
});

// текст подписи: id (RSSI, Dist)
const rssiPart = computed(() => (typeof props.data?.rssi === 'number') ? `${props.data!.rssi} dBm` : '');
const distPart = computed(() => (radius.value != null) ? `${radius.value!.toFixed(1)} м` : '');
const labelText = computed(() => {
	const parts = [rssiPart.value, distPart.value].filter(Boolean).join(', ');
	return parts ? `${props.beacon.id} (${parts})` : props.beacon.id;
});
</script>
