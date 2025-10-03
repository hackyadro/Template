<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue"

const props = defineProps<{
  beacons: { name: string; x: number; y: number }[]
  path: { x: number; y: number }[]
  position: { x: number; y: number } | null
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null

const scale = ref(1)
const origin = { x: 0, y: 0 }

const width = ref(800)
const height = ref(600)

const MIN_SCALE = 10
const MAX_SCALE = 100

// drag-to-pan
let isDragging = false
let lastX = 0
let lastY = 0

function draw() {
  if (!ctx) return
  ctx.clearRect(0, 0, width.value, height.value)

  // Сетка — через (0,0)
  ctx.strokeStyle = "#ddd"
  ctx.lineWidth = 1
  const gridStep = 1 * scale.value // 1 метр = 1 клетка

  const centerX = width.value / 2 - origin.x
  const centerY = height.value / 2 + origin.y

  // Вертикальные линии
  for (let x = centerX % gridStep; x < width.value; x += gridStep) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height.value)
    ctx.stroke()
  }

  // Горизонтальные линии
  for (let y = centerY % gridStep; y < height.value; y += gridStep) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width.value, y)
    ctx.stroke()
  }

  // Оси
  ctx.strokeStyle = "#999"
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width.value, centerY)
  ctx.stroke()

  ctx.beginPath()
  ctx.moveTo(centerX, 0)
  ctx.lineTo(centerX, height.value)
  ctx.stroke()

  // маяки
  ctx.fillStyle = "blue"
  ctx.font = "14px Arial"
  ctx.textAlign = "center"
  for (const b of props.beacons) {
    const { cx, cy } = toCanvasCoords(b.x, b.y)
    ctx.beginPath()
    ctx.arc(cx, cy, 5, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = "black"
    ctx.fillText(b.name, cx, cy - 10)
    ctx.fillStyle = "blue"
  }

  // путь
  if (props.path.length > 1) {
    ctx.strokeStyle = "green"
    ctx.lineWidth = 2
    ctx.beginPath()
    const start = toCanvasCoords(props.path[0].x, props.path[0].y)
    ctx.moveTo(start.cx, start.cy)
    for (let i = 1; i < props.path.length; i++) {
      const { cx, cy } = toCanvasCoords(props.path[i].x, props.path[i].y)
      ctx.lineTo(cx, cy)
    }
    ctx.stroke()
  }

  // позиция пользователя
  if (props.position) {
    const { cx, cy } = toCanvasCoords(props.position.x, props.position.y)
    ctx.fillStyle = "red"
    ctx.beginPath()
    ctx.arc(cx, cy, 6, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = "black"
    ctx.fillText(
      `(${props.position.x.toFixed(1)}, ${props.position.y.toFixed(1)})`,
      cx,
      cy + 16
    )
  }

  // линейка масштаба
  drawScaleBar()
}

function toCanvasCoords(x: number, y: number) {
  const cx = width.value / 2 + x * scale.value - origin.x
  const cy = height.value / 2 - y * scale.value + origin.y
  return { cx, cy }
}

function drawScaleBar() {
  if (!ctx) return
  const barLengthMeters = 10
  const barLengthPixels = barLengthMeters * scale.value

  const startX = 40
  const startY = height.value - 40

  ctx.strokeStyle = "black"
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(startX, startY)
  ctx.lineTo(startX + barLengthPixels, startY)
  ctx.stroke()

  ctx.fillStyle = "black"
  ctx.font = "14px Arial"
  ctx.fillText(`${barLengthMeters} m`, startX + barLengthPixels / 2, startY - 5)
}

function handleWheel(e: WheelEvent) {
  e.preventDefault()
  const zoomFactor = 1.05
  if (e.deltaY < 0) {
    scale.value = Math.min(scale.value * zoomFactor, MAX_SCALE)
  } else {
    scale.value = Math.max(scale.value / zoomFactor, MIN_SCALE)
  }
  draw()
}

// drag events
function handleMouseDown(e: MouseEvent) {
  isDragging = true
  lastX = e.clientX
  lastY = e.clientY
}
function handleMouseMove(e: MouseEvent) {
  if (!isDragging) return
  const dx = e.clientX - lastX
  const dy = e.clientY - lastY
  origin.x -= dx
  origin.y += dy
  lastX = e.clientX
  lastY = e.clientY
  draw()
}
function handleMouseUp() {
  isDragging = false
}

function resizeCanvas() {
  if (!canvas.value) return
  width.value = window.innerWidth
  height.value = window.innerHeight * 0.8
  canvas.value.width = width.value
  canvas.value.height = height.value

  const targetWorldSize = 100
  const fitScale = Math.min(width.value, height.value) / targetWorldSize
  scale.value = fitScale

  draw()
}

onMounted(() => {
  if (!canvas.value) return
  ctx = canvas.value.getContext("2d")
  resizeCanvas()
  canvas.value.addEventListener("wheel", handleWheel)
  canvas.value.addEventListener("mousedown", handleMouseDown)
  canvas.value.addEventListener("mousemove", handleMouseMove)
  canvas.value.addEventListener("mouseup", handleMouseUp)
  window.addEventListener("resize", resizeCanvas)
})

onUnmounted(() => {
  canvas.value?.removeEventListener("wheel", handleWheel)
  canvas.value?.removeEventListener("mousedown", handleMouseDown)
  canvas.value?.removeEventListener("mousemove", handleMouseMove)
  canvas.value?.removeEventListener("mouseup", handleMouseUp)
  window.removeEventListener("resize", resizeCanvas)
})

watch(
  () => [props.beacons, props.path, props.position, scale.value, origin.x, origin.y],
  draw,
  { deep: true }
)
</script>

<template lang="pug">
canvas(ref="canvas" class="map-canvas")
</template>

<style scoped>
.map-canvas {
  display: block;
  width: 100vw;
  height: 100vh;
  cursor: grab;
}
.map-canvas:active {
  cursor: grabbing;
}
</style>