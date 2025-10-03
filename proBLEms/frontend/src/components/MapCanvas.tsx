import { useEffect, useRef, useState, useCallback } from 'react';
import type { Beacon, Position } from '@/types';

interface MapCanvasProps {
  beacons: Beacon[];
  positions: Position[];
  currentPosition?: Position;
  width?: number;
  height?: number;
}

export const MapCanvas = ({
                            beacons,
                            positions,
                            currentPosition,
                            width = 800,
                            height = 600
                          }: MapCanvasProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // масштаб: пикселей на метр
  const [scale, setScale] = useState(50);
  // смещение "начала координат" (0,0) в пикселях от левого-верхнего угла canvas
  const [offset, setOffset] = useState({ x: 50, y: 50 });

  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // === координатное преобразование (мировые -> экранные) ===
  // ВАЖНО: инвертируем Y, чтобы положительные Y шли вверх экрана.
  const worldToCanvas = useCallback(
      (wx: number, wy: number) => ({
        x: offset.x + wx * scale,
        y: offset.y - wy * scale
      }),
      [offset, scale]
  );

  const handleMouseDown = useCallback(
      (e: React.MouseEvent<HTMLCanvasElement>) => {
        setIsDragging(true);
        setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
      },
      [offset]
  );

  const handleMouseMove = useCallback(
      (e: React.MouseEvent<HTMLCanvasElement>) => {
        if (!isDragging) return;
        setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
      },
      [isDragging, dragStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale(prev => Math.max(10, Math.min(200, prev * delta)));
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw
    drawGrid(ctx, canvas.width, canvas.height);
    drawBeacons(ctx, beacons);
    drawPath(ctx, positions);
    if (currentPosition) drawCurrentPosition(ctx, currentPosition);
  }, [beacons, positions, currentPosition, scale, offset, worldToCanvas]);

  // === GRID ===
  const drawGrid = (ctx: CanvasRenderingContext2D, w: number, h: number) => {
    const originX = offset.x;
    const originY = offset.y;

    // линия сетки
    ctx.strokeStyle = 'hsl(215 20% 92%)';
    ctx.lineWidth = 1;
    ctx.font = '10px system-ui';
    ctx.fillStyle = 'hsl(215 25% 45%)';

    // Вертикальные линии (мировые X = i)
    // i от floor(-originX/scale) до ceil((w - originX)/scale)
    for (let i = Math.floor(-originX / scale); i <= Math.ceil((w - originX) / scale); i++) {
      const x = originX + i * scale;
      if (x < 0 || x > w) continue;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();

      // подписи по X на оси X (где y=0 -> экранная y = originY)
      if (originY > 10 && originY < h - 10) {
        ctx.fillText(i.toString(), x - 5, originY + 15);
      }
    }

    // Горизонтальные линии (мировые Y = i)
    // Мэппинг: screenY = originY - i*scale
    // Для покрытия экрана: i от floor((originY - h)/scale) до ceil(originY/scale)
    for (let i = Math.floor((originY - h) / scale); i <= Math.ceil(originY / scale); i++) {
      const y = originY - i * scale;
      if (y < 0 || y > h) continue;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();

      // подписи по Y на оси Y (где x=0 -> экранная x = originX)
      if (originX > 20 && originX < w - 20) {
        // РАНЬШЕ было -i. Теперь ось инвертирована в рендере, так что показываем i как есть.
        ctx.fillText(i.toString(), originX - 20, y + 4);
      }
    }

    // Оси координат
    ctx.strokeStyle = 'hsl(215 25% 25%)';
    ctx.lineWidth = 2;

    // Ось X (мировая y=0 -> экранная y = originY)
    if (originY >= 0 && originY <= h) {
      ctx.beginPath();
      ctx.moveTo(0, originY);
      ctx.lineTo(w, originY);
      ctx.stroke();

      // стрелка и подпись X
      ctx.beginPath();
      ctx.moveTo(w - 10, originY - 5);
      ctx.lineTo(w, originY);
      ctx.lineTo(w - 10, originY + 5);
      ctx.stroke();

      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.font = 'bold 12px system-ui';
      ctx.fillText('X', w - 20, originY - 10);
    }

    // Ось Y (мировая x=0 -> экранная x = originX)
    if (originX >= 0 && originX <= w) {
      ctx.beginPath();
      ctx.moveTo(originX, 0);
      ctx.lineTo(originX, h);
      ctx.stroke();

      // стрелка вверх (положительное Y теперь визуально вверх)
      ctx.beginPath();
      ctx.moveTo(originX - 5, 10);
      ctx.lineTo(originX, 0);
      ctx.lineTo(originX + 5, 10);
      ctx.stroke();

      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.font = 'bold 12px system-ui';
      ctx.fillText('Y', originX + 10, 15);
    }

    // Точка (0,0)
    if (originX >= 0 && originX <= w && originY >= 0 && originY <= h) {
      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.beginPath();
      ctx.arc(originX, originY, 4, 0, 2 * Math.PI);
      ctx.fill();

      ctx.font = 'bold 11px system-ui';
      ctx.fillText('(0,0)', originX + 8, originY + 15);
    }
  };

  // === BEACONS ===
  const drawBeacons = (ctx: CanvasRenderingContext2D, list: Beacon[]) => {
    list.forEach(b => {
      const { x, y } = worldToCanvas(b.x, b.y);

      // круг маяка
      ctx.fillStyle = 'hsl(355 85% 55%)';
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, 2 * Math.PI);
      ctx.fill();

      // подпись
      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.font = 'bold 12px system-ui';
      ctx.fillText(b.id, x + 12, y + 5);

      // радиус сигнала (декор)
      ctx.strokeStyle = 'hsla(355 85% 55% / 0.2)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(x, y, 30, 0, 2 * Math.PI);
      ctx.stroke();
    });
  };

  // === PATH ===
  const drawPath = (ctx: CanvasRenderingContext2D, pts: Position[]) => {
    if (pts.length < 2) return;

    ctx.strokeStyle = 'hsl(215 15% 45%)';
    ctx.lineWidth = 2;

    const first = pts[0];
    const p0 = worldToCanvas(first.x, first.y);

    ctx.beginPath();
    ctx.moveTo(p0.x, p0.y);

    for (let i = 1; i < pts.length; i++) {
      const p = worldToCanvas(pts[i].x, pts[i].y);
      ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();

    // точки на пути
    pts.forEach(pos => {
      const { x, y } = worldToCanvas(pos.x, pos.y);
      ctx.fillStyle = 'hsl(215 15% 45%)';
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  };

  // === CURRENT POSITION ===
  const drawCurrentPosition = (ctx: CanvasRenderingContext2D, pos: Position) => {
    const { x, y } = worldToCanvas(pos.x, pos.y);

    // точность
    if (pos.accuracy) {
      ctx.fillStyle = 'hsla(210 90% 48% / 0.1)';
      ctx.beginPath();
      ctx.arc(x, y, pos.accuracy * scale, 0, 2 * Math.PI);
      ctx.fill();

      ctx.strokeStyle = 'hsla(210 90% 48% / 0.3)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, pos.accuracy * scale, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // сам маркер
    ctx.fillStyle = 'hsl(210 90% 48%)';
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, 2 * Math.PI);
    ctx.fill();

    // белая обводка
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, 2 * Math.PI);
    ctx.stroke();
  };

  return (
      <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="border border-border rounded-lg bg-card cursor-move"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
      />
  );
};
