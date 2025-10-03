<script>
    import { systemStatus, currentPosition, beacons, realTimePath } from '../stores.js';
    import { websocketService } from '../connection.js';

    let frequency = 1;
    let beaconFile;
    export let url = 'ws://localhost:8000/ws/wanderer';

    async function sendBeaconsOnServer() {
        try {
            const response = await fetch('http://localhost:8000/beacons', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    beacons: $beacons
                })
            });

            if (!response.ok) {
                throw new Error(`Error status: ${response.status}`);
            }

            await response.json();
            console.log("Beacons sent successfully!")
            
        } catch (error) {
            console.error('Error sending beacons:', error);
        }
    }

    async function startRouteOnServer(newFreq) {
        try {
            if (newFreq > 10 || newFreq < 0.1) {
                throw new Error('Incorrect frequency');
            }
            const response = await fetch('http://localhost:8000/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    freq: newFreq
                })
            });

            if (!response.ok) {
                throw new Error(`Error status: ${response.status}`);
            }

            await response.json();
            console.log("Starting success!")
            
        } catch (error) {
            console.error('Error starting route:', error);
        }
    }

    async function stopRouteOnServer() {
        try {
            const response = await fetch('http://localhost:8000/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`Error status: ${response.status}`);
            }

            await response.json();
            console.log("Stopping success!")
            
        } catch (error) {
            console.error('Error stopping route:', error);
        }
    }

    function loadBeacons(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            const parsedBeacons = parseBeaconsFile(content);
            beacons.set(parsedBeacons);
        };
        reader.readAsText(file);
    }

    function parseBeaconsFile(content) {
        const lines = content.trim().split('\n');
        const beaconsData = [];

        for (let i = 1; i < lines.length; i++) {
            const [name, x, y] = lines[i].split(';');
            if (name && x && y) {
                beaconsData.push({
                    name: name.trim(),
                    x: parseFloat(x.trim()),
                    y: parseFloat(y.trim())
                });
            }
        }

        return beaconsData;
    }

    async function startRoute() {
        try {
            await sendBeaconsOnServer();
            await startRouteOnServer(frequency);
            websocketService.flag = false;
            websocketService.connect(url);
            systemStatus.update(status => ({
                ...status,
                isRecording: true,
                frequency: frequency
            }));
        } catch (error) {
            console.error('Error with starting route');
        }
    }

    async function stopRoute() {
        try {
            await stopRouteOnServer();
            websocketService.flag = true;
            websocketService.disconnect(url);
            systemStatus.update(status => ({
                ...status,
                isRecording: false
            }));
        } catch (error) {
            console.error('Error with starting route');
        }
    }

    function exportPath() {
        const pathContent = generatePathFile();
        downloadFile(pathContent, 'route.path', 'text/plain');
    }

    function generatePathFile() {
        let content = 'X;Y\n';
        $realTimePath.forEach(point => {
            content += `${point.x.toFixed(2)};${point.y.toFixed(2)}\n`;
        });
        return content;
    }

    function downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    $: if (frequency !== $systemStatus.frequency) {
        systemStatus.update(status => ({
            ...status,
            frequency: frequency
        }));
    }
</script>

<div class="control-panel">
    <h2>Управление навигацией</h2>

    <div class="control-group">
        <h3>Маяки</h3>
        <input
            type="file"
            accept=".beacons"
            bind:this={beaconFile}
            on:change={loadBeacons}
        />
        <div class="beacons-list">
            {#each $beacons as beacon}
                <div class="beacon-item">
                    {beacon.name}: ({beacon.x}, {beacon.y})
                </div>
            {/each}
        </div>
    </div>

    <div class="control-group">
        <h3>Маршрут</h3>
        <label>
            Частота обновления (Гц):
            <input type="number" bind:value={frequency} min="0.1" max="10" step="0.1" disabled={$systemStatus.isRecording}/>
        </label>

        <div class="button-group">
            {#if !$systemStatus.isRecording}
                <button on:click={startRoute} class="start-btn" disabled={!$beacons || $beacons.length === 0}>
                    ▶ Начать маршрут
                </button>
            {:else}
                <button on:click={stopRoute} class="stop-btn" disabled={!$beacons || $beacons.length === 0}>
                    ⏹ Остановить
                </button>
            {/if}
        </div>
    </div>

    <div class="control-group">
        <h3>Экспорт данных</h3>
        <button on:click={exportPath} disabled={$realTimePath.length === 0}>
            💾 Экспорт маршрута (.path)
        </button>
        <div class="path-info">
            Точек в маршруте: {$realTimePath.length}
        </div>
    </div>
</div>

<style>
    .control-panel {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    .control-panel h2 {
      margin: 0;
    }

    .control-group h3 {
      color: #475569;
      font-weight: 600;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .control-group {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }

    .control-group h3 {
        margin: 0 0 10px 0;
        font-size: 16px;
        color: #333;
    }

    .beacons-list {
        margin-top: 10px;
        max-height: 150px;
        overflow-y: auto;
    }

    .beacon-item {
        padding: 5px;
        border-bottom: 1px solid #eee;
        font-size: 12px;
    }

    .button-group {
        display: flex;
        gap: 10px;
        margin-top: 10px;
    }

    button {
        padding: 10px 15px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        width: 100%;
        font-size: 14px;
    }

    .start-btn {
        background: #28a745;
        color: white;
        width: 100%;
    }

    .stop-btn {
        background: #dc3545;
        color: white;
    }

    button:disabled {
        background: #6c757d;
        cursor: not-allowed;
    }

    label {
        display: block;
        margin-bottom: 10px;
    }

    input[type="number"] {
        width: 80px;
        padding: 5px;
        border: 1px solid #ddd;
        border-radius: 4px;
    }

    input[type="file"] {
        width: 100%;
    }

    .path-info {
        margin-top: 10px;
        font-size: 12px;
        color: #666;
    }
</style>
