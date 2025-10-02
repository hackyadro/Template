<template>
	<g v-if="pos" class="device">
		<circle :cx="pos.x" :cy="pos.y" :r="outerR" fill="#e53935"/>
		<circle :cx="pos.x" :cy="pos.y" :r="innerR" fill="#fff" opacity="0.9"/>
		<text :x="pos.x" :y="pos.y - labelDy" class="lbl">ESP</text>
	</g>
</template>

<script setup lang="ts">
import {computed} from 'vue';
import type {Point} from '../types';

const props = defineProps<{
	pos: Point | null | undefined;
	baseR?: number;     // м
	labelDy?: number;   // м
}>();

const baseR = computed<number>(() => props.baseR ?? 0.15);
const outerR = computed<number>(() => baseR.value * 1.25);
const innerR = computed<number>(() => baseR.value * 0.5);
const labelDy = computed<number>(() => props.labelDy ?? 0.25);
</script>

<style scoped>
.lbl {
	font-size: 0.25px;
	text-anchor: middle;
	dominant-baseline: central;
	fill: #111;
	paint-order: stroke;
	stroke: #fff;
	stroke-width: 0.05px;
}
</style>
