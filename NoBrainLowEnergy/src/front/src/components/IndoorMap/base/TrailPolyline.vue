<template>
	<polyline
		v-if="points?.length"
		:points="points.map(p => `${p.x},${p.y}`).join(' ')"
		fill="none" stroke="#8a2be2" stroke-width="0.06" opacity="0.6"
	/>
</template>

<script setup lang="ts">
import type {Point} from '../types';

defineProps<{ points: Point[] }>();
</script>
