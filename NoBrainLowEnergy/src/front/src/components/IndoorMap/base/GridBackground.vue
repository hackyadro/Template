<template>
	<g shape-rendering="crispEdges">
		<defs>
			<pattern :id="patternId" patternUnits="userSpaceOnUse" :width="S" :height="S">
				<!-- линии только сверху/слева, чтобы не было двойных штрихов -->
				<path :d="`M 0 0 H ${S}`"
				      stroke="black" stroke-opacity="0.25" stroke-width="1"
				      vector-effect="non-scaling-stroke"/>
				<path :d="`M 0 0 V ${S}`"
				      stroke="black" stroke-opacity="0.25" stroke-width="1"
				      vector-effect="non-scaling-stroke"/>
			</pattern>
		</defs>

		<!-- ГЛАВНОЕ: сетка на всю видимую область (может выходить за комнату) -->
		<rect
			:x="viewRect?.x ?? 0"
			:y="viewRect?.y ?? 0"
			:width="viewRect?.w ?? room.w"
			:height="viewRect?.h ?? room.h"
			:fill="`url(#${patternId})`"
		/>

		<!-- рамка комнаты -->
		<rect x="0" y="0" :width="room.w" :height="room.h"
		      fill="none" stroke="black" stroke-opacity="0.35" stroke-width="1"
		      vector-effect="non-scaling-stroke"/>

		<!-- опциональный фон-план — только внутри комнаты -->
		<image v-if="backgroundUrl"
		       :href="backgroundUrl"
		       x="0" y="0" :width="room.w" :height="room.h"
		       preserveAspectRatio="none" opacity="0.35"/>
	</g>
</template>

<script setup lang="ts">
import {computed, ref} from 'vue';
import type {Room} from '../types';

const props = defineProps<{
	room: Room;
	gridCellSize: number;
	backgroundUrl?: string;
	/** ВИДИМЫЙ прямоугольник (в координатах комнаты), чтобы растягивать сетку за её пределы */
	viewRect?: { x: number; y: number; w: number; h: number };
}>();

const patternId = ref<string>(`grid-${Math.random().toString(36).slice(2, 8)}`);
const S = computed(() => props.gridCellSize);
</script>
