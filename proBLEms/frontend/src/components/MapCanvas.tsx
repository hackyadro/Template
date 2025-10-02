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
  const [scale, setScale] = useState(50); // pixels per meter
  const [offset, setOffset] = useState({ x: 50, y: 50 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  }, [offset]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  }, [isDragging, dragStart]);

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

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    drawGrid(ctx, canvas.width, canvas.height);

    // Draw beacons
    drawBeacons(ctx, beacons);

    // Draw path
    drawPath(ctx, positions);

    // Draw current position
    if (currentPosition) {
      drawCurrentPosition(ctx, currentPosition);
    }
  }, [beacons, positions, currentPosition, scale, offset]);

  const drawGrid = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    // Находим положение точки (0,0) на canvas
    const originX = offset.x;
    const originY = offset.y;

    // Рисуем сетку
    ctx.strokeStyle = 'hsl(215 20% 92%)';
    ctx.lineWidth = 1;
    ctx.font = '10px system-ui';
    ctx.fillStyle = 'hsl(215 25% 45%)';

    // Вертикальные линии (параллельно оси Y)
    for (let i = Math.floor(-originX / scale); i <= Math.ceil((width - originX) / scale); i++) {
      const x = originX + i * scale;
      if (x < 0 || x > width) continue;
      
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();

      // Метки на оси X (только если рядом с осью X)
      if (Math.abs(originY) < height && originY > 10 && originY < height - 10) {
        ctx.fillText(i.toString(), x - 5, originY + 15);
      }
    }

    // Горизонтальные линии (параллельно оси X)
    for (let i = Math.floor(-originY / scale); i <= Math.ceil((height - originY) / scale); i++) {
      const y = originY + i * scale;
      if (y < 0 || y > height) continue;
      
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();

      // Метки на оси Y (только если рядом с осью Y)
      if (Math.abs(originX) < width && originX > 20 && originX < width - 20) {
        ctx.fillText((-i).toString(), originX - 20, y + 4);
      }
    }

    // Рисуем оси координат
    ctx.strokeStyle = 'hsl(215 25% 25%)';
    ctx.lineWidth = 2;

    // Ось X
    if (originY >= 0 && originY <= height) {
      ctx.beginPath();
      ctx.moveTo(0, originY);
      ctx.lineTo(width, originY);
      ctx.stroke();

      // Стрелка на оси X
      ctx.beginPath();
      ctx.moveTo(width - 10, originY - 5);
      ctx.lineTo(width, originY);
      ctx.lineTo(width - 10, originY + 5);
      ctx.stroke();

      // Подпись оси X
      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.font = 'bold 12px system-ui';
      ctx.fillText('X', width - 20, originY - 10);
    }

    // Ось Y
    if (originX >= 0 && originX <= width) {
      ctx.beginPath();
      ctx.moveTo(originX, 0);
      ctx.lineTo(originX, height);
      ctx.stroke();

      // Стрелка на оси Y
      ctx.beginPath();
      ctx.moveTo(originX - 5, 10);
      ctx.lineTo(originX, 0);
      ctx.lineTo(originX + 5, 10);
      ctx.stroke();

      // Подпись оси Y
      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.font = 'bold 12px system-ui';
      ctx.fillText('Y', originX + 10, 15);
    }

    // Точка отсчета (0,0)
    if (originX >= 0 && originX <= width && originY >= 0 && originY <= height) {
      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.beginPath();
      ctx.arc(originX, originY, 4, 0, 2 * Math.PI);
      ctx.fill();

      // Подпись (0,0)
      ctx.font = 'bold 11px system-ui';
      ctx.fillText('(0,0)', originX + 8, originY + 15);
    }
  };

  const drawBeacons = (ctx: CanvasRenderingContext2D, beacons: Beacon[]) => {
    beacons.forEach(beacon => {
      const x = offset.x + beacon.x * scale;
      const y = offset.y + beacon.y * scale;

      // Draw beacon circle
      ctx.fillStyle = 'hsl(355 85% 55%)';
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, 2 * Math.PI);
      ctx.fill();

      // Draw beacon label
      ctx.fillStyle = 'hsl(215 25% 15%)';
      ctx.font = 'bold 12px system-ui';
      ctx.fillText(beacon.id, x + 12, y + 5);

      // Draw signal radius
      ctx.strokeStyle = 'hsla(355 85% 55% / 0.2)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(x, y, 30, 0, 2 * Math.PI);
      ctx.stroke();
    });
  };

  const drawPath = (ctx: CanvasRenderingContext2D, positions: Position[]) => {
    if (positions.length < 2) return;

    ctx.strokeStyle = 'hsl(215 15% 45%)';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const first = positions[0];
    const startX = offset.x + first.x * scale;
    const startY = offset.y + first.y * scale;
    ctx.moveTo(startX, startY);

    for (let i = 1; i < positions.length; i++) {
      const pos = positions[i];
      const x = offset.x + pos.x * scale;
      const y = offset.y + pos.y * scale;
      ctx.lineTo(x, y);
    }

    ctx.stroke();

    // Draw position points
    positions.forEach(pos => {
      const x = offset.x + pos.x * scale;
      const y = offset.y + pos.y * scale;
      
      ctx.fillStyle = 'hsl(215 15% 45%)';
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  };

  const drawCurrentPosition = (ctx: CanvasRenderingContext2D, position: Position) => {
    const x = offset.x + position.x * scale;
    const y = offset.y + position.y * scale;

    // Draw accuracy circle
    if (position.accuracy) {
      ctx.fillStyle = 'hsla(210 90% 48% / 0.1)';
      ctx.beginPath();
      ctx.arc(x, y, position.accuracy * scale, 0, 2 * Math.PI);
      ctx.fill();

      ctx.strokeStyle = 'hsla(210 90% 48% / 0.3)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, position.accuracy * scale, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // Draw current position
    ctx.fillStyle = 'hsl(210 90% 48%)';
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, 2 * Math.PI);
    ctx.fill();

    // Draw white border
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
