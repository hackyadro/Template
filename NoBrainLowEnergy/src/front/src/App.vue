<template>
	<IndoorMap
		:room="{ w: 12, h: 8 }"
		:beacons="beacons"
		:beaconData="beaconData"
		:device="device"
		:trail="trail"
		:grid-cell-size="1"
		:ring-options="{ color:'#2196f3', fillOpacity:0.10, strokeOpacity:0.35, max:6 }"
	/>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import IndoorMap from './components/IndoorMap/IndoorMap.vue';
import type { Point } from './components/IndoorMap/types';

const beacons = [
	{ id: 'b01', x: 1.0,  y: 1.0 },
	{ id: 'b02', x: 11.0, y: 1.2 },
	{ id: 'b03', x: 6.0,  y: 7.2 },
];

// эти данные вы обновляете по MQTT
const beaconData = reactive<Record<string, { rssi?: number; dist?: number }>>({
	b01: { rssi: -57, dist: 5.3 },
	b02: { rssi: -61, dist: 3.1 },
	b03: { rssi: -63, dist: 1.8 },
});

const device = ref<Point|null>({ x: 5.0, y: 3.5 });
const trail  = ref<Point[]>([
	{x: 2.0, y: 2.0},
	{x: 3.0, y: 3.5}
]);
</script>
