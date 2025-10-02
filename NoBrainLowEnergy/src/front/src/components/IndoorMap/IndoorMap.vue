<template>
	<div class="map-wrap">
		<svg class="map-svg" :viewBox="`0 0 ${room.w} ${room.h}`" preserveAspectRatio="xMidYMid meet">
			<GridBackground :room="room" :gridCellSize="gridCellSize" :backgroundUrl="backgroundUrl" />
			<BeaconsLayer
				:room="room"
				:beacons="beacons"
				:data="beaconData"
				:ring="ringOptions"
				:markerR="markerR"
				:labelDy="labelDy"
			/>
			<TrailPolyline v-if="trail?.length" :points="trail!" />
			<DeviceMarker :pos="device" :baseR="markerR" :labelDy="labelDy" />
		</svg>
	</div>
</template>


<script setup lang="ts">
import { toRefs } from 'vue';
import type { Beacon, Point, Room, RingOptions, BeaconData } from './types';

import GridBackground from './base/GridBackground.vue';
import BeaconsLayer   from './base/BeaconsLayer.vue';
import TrailPolyline  from './base/TrailPolyline.vue';
import DeviceMarker   from './base/DeviceMarker.vue';

const props = defineProps<{
	room: Room;
	beacons: Beacon[];
	beaconData?: Record<string, BeaconData>; // { [id]: { rssi?, dist? } }
	device?: Point | null;
	trail?: Point[];
	backgroundUrl?: string;
	gridCellSize?: number;
	ringOptions?: RingOptions;               // стили круга
}>();

const { room, beacons, beaconData, device, trail, backgroundUrl } = toRefs(props);

// визуальные параметры
const markerR = 0.15;
const labelDy = 0.25;
const gridCellSize = props.gridCellSize ?? 1;

// дефолтные стили кругов (можете переопределить через :ring-options)
const ringOptions: RingOptions = {
	color: '#0b84f3',
	fillOpacity: 0.12,
	strokeOpacity: 0.35,
	min: 0, max: 0
};
Object.assign(ringOptions, props.ringOptions ?? {});
</script>

<style scoped>
.map-wrap { position: relative; width: 100%; height: 100%; min-height: 320px; background: #fafafa; }
.map-svg  { width: 100%; height: 100%; display: block; }
</style>
