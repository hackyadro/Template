const SCALE = 100;

const crs = L.extend({}, L.CRS.Simple, {
  transformation: new L.Transformation(SCALE, 0, -SCALE, 0)
});

const map = L.map("map", {
  crs: crs,
  zoomControl: true,
  attributionControl: false,
  minZoom: -5,
  maxZoom: 5
});
map.setView([0, 0], 0);

// Маяки
// сюда подгрузим маяки
let beacons = [];

// загружаем маяки из файла
async function loadBeacons(file = "data/beacons_kpa.beacons") {
  const res = await fetch(file);
  const text = await res.text();
  const lines = text.trim().split("\n").slice(1); // пропускаем заголовок
  beacons = lines.map(line => {
    const [id, x, y] = line.split(";");
    return { id, x: parseFloat(x), y: parseFloat(y) };
  });
  console.log("Маяки загружены:", beacons);

  // рисуем маяки ТОЛЬКО после загрузки
  beacons.forEach(b => {
    const marker = L.circleMarker([b.y, b.x], {
      radius: 6,
      color: "cyan",
      fillColor: "cyan",
      fillOpacity: 1
    }).addTo(map);
    marker.bindTooltip(
      `${b.id}<br>X: ${b.x.toFixed(2)}, Y: ${b.y.toFixed(2)}`, 
      { permanent: true, direction: "right", className: "beacon-label" }
    );
  });
}

loadBeacons("data/beacons_kpa.beacons");

const grid = L.gridLayer({
  attribution: ""
});

grid.createTile = function(coords) {
  const tile = document.createElement("canvas");
  tile.width = tile.height = 256;
  const ctx = tile.getContext("2d");

  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 1;

  for (let i = 0; i <= 256; i += 32) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, 256);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(256, i);
    ctx.stroke();
  }

  return tile;
};

grid.addTo(map);

// Трекер
let trackerMarker = L.circleMarker([0,0], {
  radius: 8,
  color: "red",
  fillColor: "red",
  fillOpacity: 1
}).addTo(map);
trackerMarker.bindTooltip("Tracker", { permanent: true, direction: "right", className: "tracker-label" });

let trackLine = L.polyline([], { color: "red" }).addTo(map);

// --- Управление маршрутом ---
let recording = false;
let currentTrack = []; // массив точек маршрута

function downloadPath(points) {
  if (points.length === 0) return;

  // формируем CSV-подобный текст
  let content = "X;Y\n";
  for (const p of points) {
    // точность округлим до 4-х знаков
    content += `${p.x.toFixed(4)};${p.y.toFixed(4)}\n`;
  }

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "route.path";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

document.getElementById("startBtn").onclick = () => {
  recording = true;
  currentTrack = [];
  trackLine.setLatLngs([]);
  console.log("Маршрут начат");
};

document.getElementById("stopBtn").onclick = () => {
  recording = false;
  console.log("Маршрут завершён");
  downloadPath(currentTrack);
};

document.getElementById("freqInput").onchange = (e) => {
  let val = parseFloat(e.target.value);
  if (val < 0.1) val = 0.1;
  if (val > 10) val = 10;
  e.target.value = val;
  console.log("Новая частота опроса:", val, "Гц");
  // Отправляем на бек
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ cmd: "set_freq", value: val }));
  }
};

// --- WebSocket ---
const ws = new WebSocket("ws://localhost:8080/ws");

ws.onopen = () => console.log("[WS] connected");
ws.onclose = () => console.log("[WS] closed");
ws.onerror = e => console.error("[WS ERROR]", e);

ws.onmessage = ev => {
  try {
    const data = JSON.parse(ev.data);
    if (data.x !== undefined && data.y !== undefined) {
      const latlng = [data.y, data.x];
      trackerMarker.setLatLng(latlng);

      if (recording) {
        trackLine.addLatLng(latlng);
        currentTrack.push({ x: data.x, y: data.y });
      }

      map.panTo(latlng, { animate: true });
    }
  } catch (e) {
    console.error("WS bad msg:", ev.data);
  }
};
