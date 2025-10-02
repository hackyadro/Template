<script setup lang="ts">
import { ref, watch, onMounted } from "vue"

interface Position {
  x: number
  y: number
}

interface Beacon {
  name: string
  x: number
  y: number
}

const props = defineProps<{
  beacons: Beacon[]
  position: Position | null
  path: Position[]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)

const width = 1000
const height = 1000

// Координаты фиксированы от -50 до 50
const minX = -50
const maxX = 50
const minY = -50
const maxY = 50

const scaleX = width / (maxX - minX)
const scaleY = height / (maxY - minY)

function toCanvasCoords(x: number, y: number) {
  return {
    cx: (x - minX) * scaleX,
    cy: height - (y - minY) * scaleY // инверсия Y
  }
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext("2d")
  if (!ctx) return

  ctx.clearRect(0, 0, width, height)

  // сетка
  ctx.strokeStyle = "#ddd"
  ctx.lineWidth = 1
  for (let i = -50; i <= 50; i += 10) {
    const { cx: cx1, cy: cy1 } = toCanvasCoords(i, -50)
    const { cx: cx2, cy: cy2 } = toCanvasCoords(i, 50)
    ctx.beginPath()
    ctx.moveTo(cx1, cy1)
    ctx.lineTo(cx2, cy2)
    ctx.stroke()

    const { cx: cx3, cy: cy3 } = toCanvasCoords(-50, i)
    const { cx: cx4, cy: cy4 } = toCanvasCoords(50, i)
    ctx.beginPath()
    ctx.moveTo(cx3, cy3)
    ctx.lineTo(cx4, cy4)
    ctx.stroke()
  }

  // маяки
  ctx.fillStyle = "blue"
  ctx.font = "12px Arial"
  for (const b of props.beacons) {
    const { cx, cy } = toCanvasCoords(b.x, b.y)
    ctx.beginPath()
    ctx.arc(cx, cy, 6, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillText(b.name, cx + 8, cy - 8)
  }

  // путь (если есть)
  if (props.path && props.path.length > 1) {
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

  // текущая позиция
  if (props.position) {
    const { cx, cy } = toCanvasCoords(props.position.x, props.position.y)
    ctx.fillStyle = "red"
    ctx.beginPath()
    ctx.arc(cx, cy, 8, 0, Math.PI * 2)
    ctx.fill()
  }
}

onMounted(draw)

// следим за изменениями
watch(() => props.beacons, draw, { deep: true })
watch(() => props.position, draw, { deep: true })
watch(() => props.path, draw, { deep: true })
</script>

<template lang="pug">
canvas(ref="canvasRef" :width="width" :height="height" class="border border-gray-400")
</template>
