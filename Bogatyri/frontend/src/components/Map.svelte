<script>
    import { beacons, currentPosition, realTimePath } from '../stores.js';

    export let width = 800;
    export let height = 350;
    export let scale = 5;
    

    let canvas;


    $: drawMap($beacons, $currentPosition, $realTimePath);

    function drawMap(beaconsData, position, path) {
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, width, height);

        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        for (let x = 0; x <= width; x += scale) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        for (let y = 0; y <= height; y += scale) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        ctx.strokeStyle = '#333';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(width/2, 0);
        ctx.lineTo(width/2, height);
        ctx.moveTo(0, height/2);
        ctx.lineTo(width, height/2);
        ctx.stroke();

        beaconsData.forEach((beacon, index) => {
            const x = width/2 + beacon.x * scale;
            const y = height/2 - beacon.y * scale;

            ctx.fillStyle = '#ff4444';
            ctx.beginPath();
            ctx.arc(x, y, 8, 0, 2 * Math.PI);
            ctx.fill();

            ctx.strokeStyle = '#cc0000';
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.fillStyle = '#fff';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(index + 1, x, y);
        });

        if (path.length > 1) {
            ctx.strokeStyle = '#4285f4';
            ctx.lineWidth = 3;
            ctx.beginPath();

            const startPoint = path[0];
            const startX = width/2 + startPoint.x * scale;
            const startY = height/2 - startPoint.y * scale;
            ctx.moveTo(startX, startY);

            path.forEach(point => {
                const x = width/2 + point.x * scale;
                const y = height/2 - point.y * scale;
                ctx.lineTo(x, y);
            });

            ctx.stroke();
        }

        const posX = width/2 + position.x * scale;
        const posY = height/2 - position.y * scale;

        ctx.fillStyle = '#00c853';
        ctx.beginPath();
        ctx.arc(posX, posY, 10, 0, 2 * Math.PI);
        ctx.fill();

        ctx.strokeStyle = '#00c853';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(posX, posY, 15, 0, 2 * Math.PI);
        ctx.stroke();
    }
</script>
<div class="map">
    <canvas
        bind:this={canvas}
        width={width}
        height={height}
        class="map-canvas"
    ></canvas>
    <div class="map-info">
        Масштаб: 1:{scale} (1px = {1/scale}м)
    </div>
</div>

<style>
    .map {
        width: 100%;
    }

    .map-canvas {
        border: 1px solid #ddd;
        width: 100%;
        height: 100%;
        background: white;
        border-radius: 16px;
    }

    .map-info {
        padding-top: 5px;
        font-size: 14px;
    }
</style>
