<template>
	<g shape-rendering="crispEdges">
		<defs>
			<!-- Клетка S×S с линиями только сверху и слева (без двойного штриха на стыках) -->
			<pattern
				:id="patternId"
				patternUnits="userSpaceOnUse"
				:width="S"
				:height="S"
				x="0" y="0"
			>
				<!-- верхняя граница клетки -->
				<path :d="`M 0 0 H ${S}`"
				      stroke="black" stroke-opacity="0.25" stroke-width="1"
				      vector-effect="non-scaling-stroke"/>
				<!-- левая граница клетки -->
				<path :d="`M 0 0 V ${S}`"
				      stroke="black" stroke-opacity="0.25" stroke-width="1"
				      vector-effect="non-scaling-stroke"/>
				<!-- фон клетки (прозрачный) — без fill -->
			</pattern>
		</defs>

		<!-- заливка сеткой -->
		<rect x="0" y="0" :width="room.w" :height="room.h" :fill="`url(#${patternId})`" />

		<!-- внешняя рамка помещения -->
		<rect x="0" y="0" :width="room.w" :height="room.h"
		      fill="none" stroke="black" stroke-opacity="0.35" stroke-width="1"
		      vector-effect="non-scaling-stroke"/>

		<!-- опциональный фон-план -->
		<image v-if="backgroundUrl"
		       :href="backgroundUrl"
		       x="0" y="0" :width="room.w" :height="room.h"
		       preserveAspectRatio="none" opacity="0.35" />
	</g>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { Room } from '../types';

const props = defineProps<{
	room: Room;
	/** размер клетки, м */
	gridCellSize: number;
	backgroundUrl?: string;
}>();

// уникальный id паттерна для каждого инстанса
const patternId = ref<string>(`grid-${Math.random().toString(36).slice(2, 8)}`);

// гарантируем, что сетка «ложится» кратно ширине/высоте комнаты
// если размеры комнаты не кратны шагу — чётко предупредим (для отладки)
const S = computed<number>(() => props.gridCellSize);
if (import.meta.env?.DEV) {
	const eps = 1e-6;
	const okW = Math.abs(Math.round(props.room.w / S.value) - (props.room.w / S.value)) < eps;
	const okH = Math.abs(Math.round(props.room.h / S.value) - (props.room.h / S.value)) < eps;
	if (!okW || !okH) {
		// eslint-disable-next-line no-console
		console.warn(`[GridBackground] room size is not multiple of gridCellSize: w=${props.room.w}, h=${props.room.h}, step=${S.value}`);
	}
}
</script>
