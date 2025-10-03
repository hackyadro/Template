<template>
	<!-- смещение dx/dy гарантирует, что bbox подписи не вылезет за границы room -->
	<g :transform="`translate(${dx},${dy})`">
		<text
			ref="textEl"
			:x="x" :y="y"
			:text-anchor="anchor"
			class="lbl"
		>{{ text }}
		</text>
	</g>
</template>

<script setup lang="ts">
import {nextTick, onMounted, ref, watch} from 'vue';
import type {Room} from '../types';

const props = defineProps<{
	x: number; y: number;
	text: string;
	room: Room;
	/** отступ от границы карты, м */
	pad?: number;
	/** SVG text-anchor */
	anchor?: 'start' | 'middle' | 'end';
}>();

const textEl = ref<SVGTextElement | null>(null);
const dx = ref(0);
const dy = ref(0);

const anchor = props.anchor ?? 'middle';
const pad = props.pad ?? 0.1; // 10 см по умолчанию

const clampOnce = () => {
	const el = textEl.value;
	if (!el) return;
	const bb = el.getBBox(); // в «метрах» (user units)
	let offX = 0, offY = 0;

	if (bb.x < pad) offX += (pad - bb.x);
	if (bb.y < pad) offY += (pad - bb.y);
	if (bb.x + bb.width > props.room.w - pad) offX += (props.room.w - pad) - (bb.x + bb.width);
	if (bb.y + bb.height > props.room.h - pad) offY += (props.room.h - pad) - (bb.y + bb.height);

	dx.value = offX;
	dy.value = offY;
};

// пересчёт при изменении текста/позиции/размера комнаты
const scheduleClamp = () => nextTick(clampOnce);

onMounted(scheduleClamp);
watch(() => [props.text, props.x, props.y, props.room.w, props.room.h], scheduleClamp);
</script>

<style scoped>
.lbl {
	/* размер в «метрах», масштабируется с картой */
	font-size: 0.25px;
	fill: #111;
	text-anchor: middle;
	dominant-baseline: central;
	paint-order: stroke;
	stroke: #fff;
	stroke-width: 0.05px;
}
</style>
