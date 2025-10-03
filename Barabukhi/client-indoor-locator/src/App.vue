<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';

const HOST_ADDRESS = "10.145.244.78:8000"

// Типы
interface Beacon {
  name: string;
  x: number;
  y: number;
}

interface Map {
  id: number;
  name: string;
  beacons: Beacon[];
  createdAt: Date;
}

interface PathPoint {
  x: number;
  y: number;
  timestamp: Date;
}

interface Device {
  id: string;
  mac: string;
  color: string;
  pollFrequency: number; // Hz
  mapId: number | null;
  path: PathPoint[];
  isPolling: boolean;
  visible: boolean;
  baseX: number | null;
  baseY: number | null;
}

// Состояние
const maps = ref<Map[]>([]);
const selectedMapId = ref<number | null>(null);
const newMapName = ref('');
const newMapBeacons = ref('');
// Устройства
const devices = ref<Device[]>([]);

// WebSocket: состояние и помощники
const ws = ref<WebSocket | null>(null);
const wsReady = ref(false);
const backendWsUrl = ref<string>(`ws://${HOST_ADDRESS}/ws`);

type InMsg = { type: string; data: any };
type OutMsg = { type: string; data: any };

// helpers
const toNumOrNull = (v: any): number | null => {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

const sendWs = (msg: OutMsg) => {
  if (ws.value && wsReady.value) {
    try {
      ws.value.send(JSON.stringify(msg));
    } catch (e) {
      console.error('WS send error', e);
    }
  } else {
    console.warn('WS is not ready');
  }
};

const downloadCoordinatesFile = (mac: string, coordinates: Array<{x: number; y: number}>) => {
  if (!coordinates || coordinates.length === 0) {
    console.warn('Нет координат для сохранения');
    return;
  }

  let content = 'X;Y\n';
  coordinates.forEach(coord => {
    const x = Number(coord.x).toFixed(1).replace('.', ',');
    const y = Number(coord.y).toFixed(1).replace('.', ',');
    content += `${x};${y}\n`;
  });

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  link.download = `road_${mac}_${timestamp}.path`;
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  
  console.log(`Файл сохранён: ${link.download}`);
};

const applyAllDevice = (data: any) => {
  const arr = Array.isArray(data) ? data : [];
  for (const d of arr) {
    const mac = d.mac as string;
    if (!mac) continue;
    const existing = devices.value.find(x => x.mac === mac);
    if (existing) {
      existing.pollFrequency = d.freq ?? existing.pollFrequency;
      existing.mapId = d.map_set;
      existing.isPolling = d.write_road ?? false;
      const bx = toNumOrNull(d.base_x);
      const by = toNumOrNull(d.base_y);
      if (bx !== null) existing.baseX = bx;
      if (by !== null) existing.baseY = by;
    } else {
      devices.value.push({
        id: Date.now().toString() + '_' + mac,
        mac,
        color: getNextColor(),
        pollFrequency: d.freq ?? 1,
        mapId: d.map_set,
        path: [],
        isPolling: d.write_road ?? false,
        visible: true,
        baseX: toNumOrNull(d.base_x),
        baseY: toNumOrNull(d.base_y),
      });
    }
  }
};

const applyListMap = (data: any) => {
  console.log(data);
  const payload = data?.maps ?? [];
  const newMaps: Map[] = [];
  for (const m of payload) {
    const beacons: Beacon[] = Array.isArray(m.beacons)
      ? m.beacons.map((b: any) => ({ name: String(b.name), x: Number(b.x), y: Number(b.y) }))
      : [];
    newMaps.push({ id: m.id, name: String(m.name), beacons, createdAt: new Date() });
  }
  if (newMaps.length > 0) {
    maps.value = newMaps;
    if (!selectedMapId.value) selectedMapId.value = newMaps[0].id;
  }
};

const handleWsMessage = (msg: InMsg) => {
  if (!msg || typeof msg.type !== 'string') return;
  if (msg.type === 'all_device') return applyAllDevice(msg.data);
  if (msg.type === 'list_map') return applyListMap(msg.data);
  if (msg.type === 'write_road') {
    const ok = !!msg.data?.ok;
    if (!ok) console.error('write_road error:', msg.data);
    return;
  }
  if (msg.type === 'position_update') {
    handlePositionUpdate(msg.data);
    return;
  }
  if (msg.type === 'last_road') {
    const d = msg.data || {};
    const mac = d?.mac;
    const roadId = d?.road_id;
    const cords = Array.isArray(d?.cords) ? d.cords : [];
    console.log('[last_road]', { mac, road_id: roadId, pointsCount: cords.length, cords });
    
    if (mac && cords.length > 0) {
      downloadCoordinatesFile(mac, cords);
    }
    return;
  }
  console.warn('Unhandled WS type:', msg.type, msg.data);
};

const handlePositionUpdate = (data: any) => {
  const mac = data.mac as string;
  const x = Number(data.x);
  const y = Number(data.y);
  const timestamp = data.timestamp ? new Date(data.timestamp * 1000) : new Date();

  const device = devices.value.find(d => d.mac === mac);
  if (!device) {
    console.warn('Position update for unknown device:', mac);
    return;
  }

  // Добавляем новую точку в путь если устройство активно (isPolling)
  // visible используется только для отображения на карте
  if (device.isPolling) {
    device.path.push({
      x,
      y,
      timestamp
    });

    // Ограничиваем историю (например, последние 100 точек)
    if (device.path.length > 10000) {
      device.path.shift();
    }
  }
};


// Вычисляемые свойства
const selectedMap = computed((): Map | undefined => 
  maps.value.find((m: Map) => m.id === selectedMapId.value)
);

// Вычисляемые коллекции для шаблона
const devicesOnSelectedMap = computed((): Device[] =>
  devices.value.filter((d: Device) => d.mapId === selectedMapId.value)
);

const hasAnyPathOnSelectedMap = computed((): boolean =>
  devicesOnSelectedMap.value.some((d: Device) => d.path.length > 0)
);

const historyRows = computed((): { device: Device; point: PathPoint }[] => {
  const rows: { device: Device; point: PathPoint }[] = [];
  for (const d of devicesOnSelectedMap.value) {
    for (const p of d.path) rows.push({ device: d, point: p });
  }
  rows.sort((a, b) => b.point.timestamp.getTime() - a.point.timestamp.getTime());
  return rows;
});

const devicesCountOnMap = computed(() => devicesOnSelectedMap.value.length);
const totalPointsOnMap = computed(() => devicesOnSelectedMap.value.reduce((acc: number, d: Device) => acc + d.path.length, 0));

// Функции для работы с картами
const parseBeacons = (text: string): Beacon[] => {
  const lines = text.trim().split('\n');
  const beacons: Beacon[] = [];
  
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.toLowerCase().startsWith('name')) continue; // Пропускаем заголовок
    
    const parts = line.split(';');
    if (parts.length === 3) {
      const name = parts[0].trim();
      const x = parseFloat(parts[1].trim());
      const y = parseFloat(parts[2].trim());
      
      if (name && !isNaN(x) && !isNaN(y)) {
        beacons.push({ name, x, y });
      }
    }
  }
  
  return beacons;
};

const saveMap = () => {
  if (!newMapName.value.trim()) {
    console.log('Введите название карты');
    return;
  }
  
  const beacons = parseBeacons(newMapBeacons.value);
  
  if (beacons.length < 3) {
    console.log('Нужно минимум 3 маяка для трилатерации');
    return;
  }
  
  sendWs({
    type: 'add_map',
    data: {
      map_name: newMapName.value.trim(),
      beacons: beacons.map(b => ({ name: b.name, x: b.x, y: b.y }))
    }
  });
  
  const newMap: Map = {
    id: Date.now(),
    name: newMapName.value.trim(),
    beacons,
    createdAt: new Date()
  };
  
  maps.value.push(newMap);
  
  // Очистка формы
  newMapName.value = '';
  newMapBeacons.value = '';
  
  // Автоматически выбираем новую карту
  selectedMapId.value = newMap.id;
};

const selectMap = (mapId: number) => {
  selectedMapId.value = mapId;
};

const deleteMap = (mapId: number) => {
  maps.value = maps.value.filter((m: Map) => m.id != mapId);
  if (selectedMapId.value === mapId) {
    selectedMapId.value = null;
  }
  // Открепляем устройства от удалённой карты и останавливаем их
  devices.value.forEach((d: Device) => {
    if (d.mapId == mapId) {
      stopDevicePolling(d.id);
      d.mapId = null;
    }
  });
};

// Устройства: логика и помощьники
const colorPalette = ['#ef4444', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#14b8a6', '#f472b6', '#22c55e', '#e11d48', '#06b6d4'];
const getNextColor = () => {
  const used = new Set(devices.value.map((d: Device) => d.color));
  const free = colorPalette.find(c => !used.has(c));
  return free || colorPalette[(devices.value.length) % colorPalette.length];
};

const removeDevice = (deviceId: string) => {
  const d = devices.value.find((x: Device) => x.id === deviceId);
  if (!d) return;
  stopDevicePolling(deviceId);
  devices.value = devices.value.filter((x: Device) => x.id !== deviceId);
};

const startDevicePolling = (deviceId: string) => {
  const d = devices.value.find((x: Device) => x.id === deviceId);
  if (!d) return;

  if (!d.mapId) {
    console.log('Выберите карту для устройства');
    return;
  }

  const m = maps.value.find((mm: Map) => mm.id == d.mapId);

  if (!m) {
    console.log('Выбранная карта не найдена');
    return;
  }
  d.isPolling = true;
  d.path = [];

  sendWs({ type: 'set_write_road', data: { mac: d.mac, status: true } });
};

const stopDevicePolling = (deviceId: string) => {
  const d = devices.value.find((x: Device) => x.id === deviceId);
  if (!d) return;
  d.isPolling = false;
  sendWs({ type: 'set_write_road', data: { mac: d.mac, status: false } });
};

const clearDevicePath = (deviceId: string) => {
  const d = devices.value.find(x => x.id === deviceId);
  if (!d) return;
  d.path = [];
};

// Установить базовые координаты устройства и сбросить предыдущий путь
const setDeviceBaseCoordinates = (device: Device) => {
  if (!device?.mac) return;
  const x = toNumOrNull(device.baseX);
  const y = toNumOrNull(device.baseY);
  if (x === null || y === null) {
    console.warn('Некорректные базовые координаты');
    return;
  }
  sendWs({ type: 'set_base_cord', data: { mac: device.mac, x, y } });
  // Сбрасываем предыдущую запись пути для устройства
  device.path = [];
};

// Запросить с сервера последнее измерение (маршрут) для устройства
const downloadLastRoad = (device: Device) => {
  if (!device?.mac) return;
  sendWs({ type: 'download_last_road', data: { mac: device.mac } });
};

// Отправляем на сервер изменение карты устройства
const handleDeviceMapChange = (device: Device) => {
  if (device.mapId == null) return;
  const m = maps.value.find((mm: Map) => mm.id === device.mapId);
  if (!m) return;
  sendWs({ type: 'set_map_to_device', data: { mac: device.mac, map_name: m.name } });
};

// Визуализация
const svgWidth = 600;
const svgHeight = 600;
const scale = ref(8);
const offsetX = ref(300);
const offsetY = ref(500);

const transformX = (x: number) => x * scale.value + offsetX.value;
const transformY = (y: number) => -y * scale.value + offsetY.value;

const devicePathD = (device: Device) => {
  if (device.path.length < 2) return '';
  let d = `M ${transformX(device.path[0].x)} ${transformY(device.path[0].y)}`;
  for (let i = 1; i < device.path.length; i++) {
    d += ` L ${transformX(device.path[i].x)} ${transformY(device.path[i].y)}`;
  }
  return d;
};

// Lifecycle
onMounted(() => {
  // Подключение к WebSocket бэкенда
  try {
    const socket = new WebSocket(backendWsUrl.value);
    ws.value = socket;
    socket.onopen = () => {
      wsReady.value = true;
      // начальные запросы
      sendWs({ type: 'get_all_device', data: {} });
      sendWs({ type: 'get_list_map', data: {} });
    };
    socket.onclose = () => {
      wsReady.value = false;
    };
    socket.onerror = () => {
      wsReady.value = false;
    };
    socket.onmessage = (ev) => {
      try {
        const packet = JSON.parse(String(ev.data));
        handleWsMessage(packet);
      } catch (e) {
        console.error('WS message parse error', e);
      }
    };
  } catch (e) {
    console.error('WS connect failed', e);
  }
});

onUnmounted(() => {
  devices.value.forEach((d: Device) => stopDevicePolling(d.id));
  if (ws.value) {
    try { ws.value.close(); } catch {}
    ws.value = null;
    wsReady.value = false;
  }
});

// Перезапуск опроса устройства при изменении его частоты
const updateDeviceFrequency = (device: Device, freq: number) => {
  device.pollFrequency = freq;
};

const handleDeviceFreqInput = (device: Device, ev: Event) => {
  const val = parseFloat((ev.target as HTMLInputElement).value);
  if (!isNaN(val)) updateDeviceFrequency(device, val);
};

// Отправляем на сервер новую частоту после отпускания ползунка
const handleDeviceFreqCommit = (device: Device) => {
  sendWs({ type: 'set_freq', data: { mac: device.mac, freq: Number(device.pollFrequency) } });
};
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <h1>🎯 Indoor Locator</h1>
      <p>Система позиционирования по BLE маякам</p>
    </header>

    <div class="main-layout">
      <!-- Левая панель: Управление картами -->
      <aside class="sidebar">
        <section class="card">
          <h2>📍 Создать карту</h2>
          
          <div class="form-group">
            <label for="mapNameInput">Название карты:</label>
            <input
              id="mapNameInput"
              v-model="newMapName"
              type="text"
              placeholder="Например: Офис 1 этаж"
              @keyup.enter="saveMap"
            />
          </div>
          
          <div class="form-group">
            <label for="mapBeaconsInput">Маяки (Name;X;Y):</label>
            <textarea
              id="mapBeaconsInput"
              v-model="newMapBeacons"
              rows="8"
              placeholder="Name;X;Y&#10;beacon_1;3.0;-2.4&#10;beacon_2;-2.4;-0.6&#10;beacon_3;1.8;9"
            ></textarea>
          </div>
          
          <button @click="saveMap" class="btn btn-primary">
            💾 Сохранить карту
          </button>
        </section>

        <section class="card">
          <h2>🗺️ Список карт</h2>
          
          <div v-if="maps.length === 0" class="empty-state">
            Карты отсутствуют. Создайте первую карту выше.
          </div>
          
          <div v-else class="map-list">
            <div 
              v-for="map in maps" 
              :key="map.id"
              :class="['map-item', { 'map-item-active': selectedMapId === map.id }]"
              @click="selectMap(map.id)"
            >
              <div class="map-item-content">
                <strong>{{ map.name }}</strong>
                <span class="map-item-info">{{ map.beacons.length }} маяков</span>
              </div>
              <button 
                type="button"
                @click.stop.prevent="deleteMap(map.id)" 
                class="btn-delete"
                title="Удалить карту"
              >
                🗑️
              </button>
            </div>
          </div>
        </section>

        <section class="card">
          <h2>🛰️ Устройства</h2>

          <div v-if="devices.length === 0" class="empty-state" style="margin-top:12px;">Пока нет устройств</div>

          <!-- Список устройств -->
          <div class="device-list" v-else>
            <div 
              class="device-item" 
              v-for="d in devices" 
              :key="d.id"
            >
              <div class="device-header">
                <div class="device-title">
                  <span class="color-dot" :style="{ background: d.color }"></span>
                  <strong>{{ d.mac }}</strong>
                </div>
                <div class="device-actions">
                  <label class="device-visible">
                    <input type="checkbox" v-model="d.visible" />
                    Показать
                  </label>
                  <button type="button" class="btn-delete" title="Удалить" @click.stop.prevent="removeDevice(d.id)">🗑️</button>
                </div>
              </div>

              <div class="device-controls">
                <div class="form-group">
                  <label :for="'mapSelect_' + d.id">Карта для устройства:</label>
                  <select :id="'mapSelect_' + d.id" v-model="d.mapId" @change="handleDeviceMapChange(d)">
                    <option :value="null">— Не выбрано —</option>
                    <option v-for="m in maps" :key="m.id" :value="m.id">{{ m.name }}</option>
                  </select>
                </div>
                <div class="form-group">
                  <label :for="'freqRange_' + d.id">
                    Частота: {{ d.pollFrequency.toFixed(1) }} Гц
                    <span class="hint">({{ Math.round(1000 / Math.max(d.pollFrequency, 0.0001)) }} мс)</span>
                  </label>
                  <input :id="'freqRange_' + d.id" type="range" min="0.1" max="10" step="0.1" :value="d.pollFrequency" @input="handleDeviceFreqInput(d, $event)" @change="handleDeviceFreqCommit(d)" />
                </div>
                <div class="form-group">
                  <div class="form-label">Base координаты (X, Y):</div>
                  <div style="display:grid; grid-template-columns: 1fr 1fr auto; gap:8px; align-items:end;">
                    <div>
                      <input
                        :id="'baseX_' + d.id"
                        type="number"
                        step="0.1"
                        placeholder="X"
                        v-model.number="d.baseX"
                      />
                    </div>
                    <div>
                      <input
                        :id="'baseY_' + d.id"
                        type="number"
                        step="0.1"
                        placeholder="Y"
                        v-model.number="d.baseY"
                      />
                    </div>
                  </div>
                </div>
                <div class="button-group">
                  <button class="btn btn-success" @click="startDevicePolling(d.id)" :disabled="d.isPolling || !d.mapId">▶️ Старт</button>
                  <button class="btn btn-danger" @click="stopDevicePolling(d.id)" :disabled="!d.isPolling">⏸️ Стоп</button>
                  <button class="btn btn-secondary" @click="clearDevicePath(d.id)" :disabled="d.path.length === 0">🗑️ Очистить</button>
                  <button class="btn btn-primary" @click="downloadLastRoad(d)">⬇️ Скачать последнее</button>
                  <button class="btn btn-primary" @click="setDeviceBaseCoordinates(d)">Set pos</button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </aside>

      <!-- Правая панель: Визуализация и данные -->
      <main class="content">
        <section class="card" v-if="selectedMap">
          <h2>🗺️ Карта: {{ selectedMap.name }}</h2>
          
          <div class="map-container">
            <svg 
              :width="svgWidth" 
              :height="svgHeight" 
              class="map-svg"
            >
              <!-- Сетка -->
              <defs>
                <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                  <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e5e7eb" stroke-width="1"/>
                </pattern>
              </defs>
              <rect :width="svgWidth" :height="svgHeight" fill="url(#grid)" />
              
              <!-- Маяки -->
              <g v-for="beacon in selectedMap.beacons" :key="beacon.name">
                <circle 
                  :cx="transformX(beacon.x)" 
                  :cy="transformY(beacon.y)" 
                  r="8" 
                  fill="#4f46e5" 
                  stroke="white" 
                  stroke-width="2"
                />
                <text 
                  :x="transformX(beacon.x)" 
                  :y="transformY(beacon.y) - 15" 
                  text-anchor="middle" 
                  font-size="12" 
                  font-weight="bold" 
                  fill="#1f2937"
                >
                  {{ beacon.name }}
                </text>
              </g>
              
              <!-- Пути и точки для устройств на выбранной карте -->
              <template v-for="d in devices">
                <template v-if="d.mapId === selectedMapId && d.visible">
                  <!-- Путь устройства -->
                  <path 
                    v-if="d.path.length >= 2" 
                    :d="devicePathD(d)" 
                    :stroke="d.color" 
                    stroke-width="3" 
                    fill="none" 
                    stroke-linejoin="round"
                    stroke-linecap="round"
                  />
                  <!-- Точки пути устройства -->
                  <circle 
                    v-for="(point, index) in d.path" 
                    :key="index + d.id"
                    :cx="transformX(point.x)" 
                    :cy="transformY(point.y)" 
                    r="4" 
                    :fill="index === d.path.length - 1 ? d.color : d.color"
                    :opacity="index === d.path.length - 1 ? 1 : 0.4"
                  />
                  <!-- Последняя позиция устройства -->
                  <g v-if="d.path.length > 0">
                    <circle 
                      :cx="transformX(d.path[d.path.length - 1].x)" 
                      :cy="transformY(d.path[d.path.length - 1].y)" 
                      r="10" 
                      :fill="d.color" 
                      stroke="white" 
                      stroke-width="3"
                    />
                    <text 
                      :x="transformX(d.path[d.path.length - 1].x)" 
                      :y="transformY(d.path[d.path.length - 1].y) + 25" 
                      text-anchor="middle" 
                      font-size="12" 
                      font-weight="bold" 
                      :fill="d.color"
                    >
                      {{ d.mac }}
                    </text>
                  </g>
                </template>
              </template>
            </svg>
          </div>
        </section>

        <section class="card" v-else>
          <div class="empty-state-large">
            <p>👈 Выберите или создайте карту для начала работы</p>
          </div>
        </section>

        <section class="card" v-if="selectedMap">
          <h2>📊 История пути</h2>
          
          <div v-if="!hasAnyPathOnSelectedMap" class="empty-state">
            Нажмите "Старт" у устройств, чтобы начать запись пути
          </div>
          
          <div v-else class="path-table-container">
            <table class="path-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Устройство</th>
                  <th>X (м)</th>
                  <th>Y (м)</th>
                  <th>Время</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, index) in historyRows"
                  :key="row.device.id + '_' + row.point.timestamp.getTime() + '_' + index"
                  :class="{ 'row-current': index === 0 }"
                >
                  <td>{{ index + 1 }}</td>
                  <td>
                    <span class="color-dot" :style="{ background: row.device.color, marginRight: '6px' }"></span>
                    {{ row.device.mac }}
                  </td>
                  <td>{{ row.point.x.toFixed(2) }}</td>
                  <td>{{ row.point.y.toFixed(2) }}</td>
                  <td>{{ row.point.timestamp.toLocaleTimeString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div class="path-stats">
            <span><strong>Устройств на карте:</strong> {{ devicesCountOnMap }}</span>
            <span style="margin-left:12px"><strong>Всего точек:</strong> {{ totalPointsOnMap }}</span>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

.app-header {
  text-align: center;
  color: white;
  margin-bottom: 30px;
}

.app-header h1 {
  margin: 0 0 10px 0;
  font-size: 2.5rem;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.app-header p {
  margin: 0;
  font-size: 1.1rem;
  opacity: 0.9;
}

.main-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card h2 {
  margin: 0 0 20px 0;
  color: #1f2937;
  font-size: 1.3rem;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
}

.form-group input[type="text"],
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: border-color 0.2s;
  font-family: inherit;
}

.form-group input[type="text"]:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-group textarea {
  resize: vertical;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.form-group input[type="range"] {
  width: 100%;
  margin-top: 8px;
}

.hint {
  color: #6b7280;
  font-weight: normal;
  font-size: 0.85rem;
}

.btn {
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.btn-success {
  background: #10b981;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #059669;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #4b5563;
}

.button-group {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.map-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.map-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.map-item:hover {
  border-color: #667eea;
  background: #f9fafb;
}

.map-item-active {
  border-color: #667eea;
  background: #eef2ff;
}

.map-item-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.map-item-info {
  font-size: 0.85rem;
  color: #6b7280;
}

.btn-delete {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-delete:hover {
  background: #fee2e2;
}

/* Устройства */
.device-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}
.device-item {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
}
.device-item-inactive {
  opacity: 0.8;
}
.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.device-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.device-mac { color: #6b7280; font-size: 0.9rem; }
.device-actions { display: flex; align-items: center; gap: 8px; }
.device-visible { font-size: 0.9rem; color: #374151; display: flex; align-items: center; gap: 6px; }
.device-controls { margin-top: 10px; }
.color-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; border: 2px solid #fff; box-shadow: 0 0 0 1px #e5e7eb; }

.empty-state {
  text-align: center;
  padding: 20px;
  color: #6b7280;
  font-style: italic;
}

.empty-state-large {
  text-align: center;
  padding: 80px 20px;
  color: #6b7280;
  font-size: 1.2rem;
}

.status-active {
  margin-top: 16px;
  padding: 12px;
  background: #d1fae5;
  border-radius: 8px;
  text-align: center;
  font-weight: 600;
  color: #065f46;
}

.map-container {
  display: flex;
  justify-content: center;
  overflow-x: auto;
}

.map-svg {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: white;
}

.path-table-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.path-table {
  width: 100%;
  border-collapse: collapse;
}

.path-table thead {
  position: sticky;
  top: 0;
  background: #f9fafb;
  z-index: 1;
}

.path-table th,
.path-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.path-table th {
  font-weight: 600;
  color: #374151;
  font-size: 0.9rem;
}

.path-table td {
  color: #1f2937;
}

.row-current {
  background: #fef3c7;
  font-weight: 600;
}

.path-stats {
  margin-top: 16px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  text-align: center;
  color: #374151;
}

@media (max-width: 1200px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
}
</style>