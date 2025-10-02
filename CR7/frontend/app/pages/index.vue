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
const path = ref<Position[]>([]); // сюда пишем маршрут
const recording = ref(false); // идёт ли запись пути

async function fetchPosition() {
  try {
    const res = await fetch("/api/position");
    const data = await res.json();
    if (data.status === "ok" || (typeof data.position.x === "number" && typeof data.position.y === "number")) {
      position.value = { x: data.position.x, y: data.position.y };

      // если идёт запись пути — добавляем в массив
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
    // начинаем новый путь
    path.value = [];
    recording.value = true;
  } else {
    // останавливаем запись
    recording.value = false;

    if (path.value.length > 0) {
      // формируем CSV
      let content = "X;Y\n";
      for (const p of path.value) {
        content += `${p.x};${p.y}\n`;
      }

      // создаём blob и качаем
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

onMounted(() => {
  fetchBeacons();
  fetchPosition();
  setInterval(fetchPosition, 1000);
});
</script>

<template lang="pug">
div.container
  h1 Indoor Map
  button(@click="toggleRecording") {{ recording ? "Завершить путь" : "Начать путь" }}
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
</style>
