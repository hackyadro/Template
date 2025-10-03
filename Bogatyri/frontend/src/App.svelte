<script>
		import Map from './components/Map.svelte';
		import ControlPanel from './components/ControlPanel.svelte';
		import StatusBar from './components/StatusBar.svelte';
    import { systemStatus, currentPosition, beacons, realTimePath } from './stores.js';

    let mapSize = { width: 800, height: 600 };
</script>

<svelte:head>
    <title>Внутренняя система навигации</title>
</svelte:head>

<div class="app">
    <header>
        <h1>Внутренняя система навигации</h1>
        <StatusBar />
    </header>

    <main class="main-content">
        <div class="map-container">
            <Map
                {mapSize}
                {beacons}
                {currentPosition}
                {realTimePath}
            />
        </div>

        <div class="controls-container">
            <ControlPanel />
        </div>
    </main>
</div>

<style>
	.app {
		padding: 24px;
		font-family: "Nunito", sans-serif;
		background: #667eea;
		height: 100vh;
		overflow-y: hidden;
	}

	header {
		margin-bottom: 24px;
		margin-top: 44px;
		padding: 20px;
		border-bottom: 2px solid rgba(255, 255, 255, 0.1);
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(10px);
		border-radius: 20px;
		padding: 20px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
	}

	header h1 {
		color: #2d3748;
		font-size: 2.5rem;
		font-weight: 700;
		text-align: left;
		margin: 0;
		background: #000;
		margin-bottom: 24px;
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.main-content {
		display: grid;
		grid-template-columns: 1fr 380px;
		gap: 24px;
		align-items: start;
	}

	.map-container {
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-radius: 24px;
		overflow: hidden;
		padding: 16px;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(10px);
		box-shadow:
				0 20px 40px rgba(0, 0, 0, 0.1),
				0 0 0 1px rgba(255, 255, 255, 0.2);
		transition: all 0.3s ease;
		max-height: 80vh;
	}

	.map-container:hover {
		box-shadow:
				0 25px 50px rgba(0, 0, 0, 0.15),
				0 0 0 1px rgba(255, 255, 255, 0.3);
		transform: translateY(-2px);
	}

	.controls-container {
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(10px);
		padding: 24px;
		border-radius: 20px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		box-shadow:
				0 20px 40px rgba(0, 0, 0, 0.1),
				0 0 0 1px rgba(255, 255, 255, 0.2);
		height: fit-content;
		position: sticky;
		top: 24px;
	}

	@media (max-width: 1024px) {
		.main-content {
				grid-template-columns: 1fr;
				gap: 20px;
		}

		.controls-container {
				position: static;
				order: -1;
		}

		header h1 {
				font-size: 2rem;
		}
		}

		@media (max-width: 768px) {
		.app {
				padding: 16px;
		}

		header {
				padding: 16px;
				margin-bottom: 20px;
		}

		header h1 {
				font-size: 1.75rem;
		}

		.map-container,
		.controls-container {
				padding: 12px;
				border-radius: 16px;
		}
	}

	@keyframes fadeIn {
		from {
				opacity: 0;
				transform: translateY(20px);
		}
		to {
				opacity: 1;
				transform: translateY(0);
		}
	}

	.app {
		animation: fadeIn 0.6s ease-out;
	}

	.map-container {
		animation: fadeIn 0.8s ease-out 0.2s both;
	}

	.controls-container {
		animation: fadeIn 0.8s ease-out 0.4s both;
	}
</style>
