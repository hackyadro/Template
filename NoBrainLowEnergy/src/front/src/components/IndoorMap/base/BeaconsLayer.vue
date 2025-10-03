<template>
	<g class="beacons">
		<BeaconItem
			v-for="b in beacons"
			:key="b.id"
			:beacon="b"
			:room="room"
			:data="data?.[b.id]"
			:ring="ring"
			:markerR="markerR"
			:labelDy="labelDy"
		/>
	</g>
</template>

<script setup lang="ts">
import {computed} from 'vue';
import BeaconItem from './BeaconItem.vue';
import type {Beacon, BeaconData, RingOptions, Room} from '../types';

const props = defineProps<{
	room: Room;
	beacons: Beacon[];
	data?: Record<string, BeaconData>;
	ring?: RingOptions;
	markerR?: number; labelDy?: number;
}>();

const markerR = computed(() => props.markerR ?? 0.15);
const labelDy = computed(() => props.labelDy ?? 0.25);
</script>
