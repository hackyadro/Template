<script setup lang="ts">
import { ref, onMounted } from "vue";
import Map from "~/components/map.vue";

interface Position {
  x: number;
  y: number;
}

interface Beacon {
  name: string;
  x: number;
  y: number;
}

const position = ref<Position | null>(null);
const beacons = ref<Beacon[]>([]);

async function fetchPosition() {
  try {
    const res = await fetch("/api/position");
    const data = await res.json();
    if (data.status === "ok" || (typeof data.x === "number" && typeof data.y === "number")) {
      position.value = { x: data.x, y: data.y };
    } else {
      position.value = null;
    }
  } catch (e) {
    console.error("Ошибка при получении позиции:", e);
  }
}

async function fetchBeacons() {
  try {
    const res = await fetch("/api/beacons");
    const data = await res.json();
    beacons.value = Object.entries(data).map(([name, coords]: [string, any]) => ({
      name,
      x: coords[0],
      y: coords[1],
    }));
  } catch (e) {
    console.error("Ошибка при получении маяков:", e);
  }
}

onMounted(() => {
  fetchBeacons();
  fetchPosition();
  setInterval(fetchPosition, 1000);
});
</script>

<template lang="pug">
div.container
  h1 Indoor Map
  Map(:position="position" :beacons="beacons")
</template>

<style scoped>
.container {
  padding: 20px;
}
</style>