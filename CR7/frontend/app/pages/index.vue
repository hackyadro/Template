<script setup lang="ts">
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
const path = ref<Position[]>([]);
const recording = ref(false);

// частота опроса (мс)
const pollingInterval = ref(1000);
let intervalId: ReturnType<typeof setInterval> | null = null;

async function fetchPosition() {
  try {
    const res = await fetch("/api/position");
    const data = await res.json();
    if (data.status === "ok" || (typeof data.position.x === "number" && typeof data.position.y === "number")) {
      position.value = { x: data.position.x, y: data.position.y };

      if (recording.value && position.value) {
        path.value.push({ ...position.value });
      }
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

function toggleRecording() {
  if (!recording.value) {
    path.value = [];
    recording.value = true;
  } else {
    recording.value = false;
    if (path.value.length > 0) {
      let content = "X;Y\n";
      for (const p of path.value) {
        content += `${p.x};${p.y}\n`;
      }
      const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sol.path";
      a.click();
      URL.revokeObjectURL(url);
    }
  }
}

function startPolling() {
  if (intervalId) clearInterval(intervalId);
  intervalId = setInterval(fetchPosition, pollingInterval.value);
}

onMounted(() => {
  fetchBeacons();
  fetchPosition();
  startPolling();
});

// пересоздаём таймер при изменении pollingInterval
watch(pollingInterval, () => {
  startPolling();
});
</script>

<template lang="pug">
div.container
  h1 Indoor Map
  button(@click="toggleRecording") {{ recording ? "Завершить путь" : "Начать путь" }}

  div.slider-container
    label Частота опроса: {{ (pollingInterval/1000).toFixed(1) }} с
    input(
      type="range"
      min="100"
      max="1000"
      step="100"
      v-model="pollingInterval"
    )

  Map(:position="position" :beacons="beacons" :path="path")
</template>

<style scoped>
.container {
  padding: 20px;
}

button {
  margin-bottom: 10px;
  padding: 8px 14px;
  border: none;
  border-radius: 6px;
  background: #007bff;
  color: white;
  font-size: 14px;
  cursor: pointer;
}
button:hover {
  background: #0056b3;
}

.slider-container {
  margin: 15px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

input[type="range"] {
  width: 200px;
}
</style>