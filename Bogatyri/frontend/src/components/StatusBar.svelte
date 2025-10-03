<script>
    import { currentPosition, systemStatus, realTimePath } from '../stores.js';
</script>

<div class="status-bar">
    <div class="status-item">
        <strong>Позиция:</strong>
        X: {$currentPosition.x.toFixed(2)},
        Y: {$currentPosition.y.toFixed(2)}
    </div>

    <div class="status-item">
        <strong>Статус:</strong>
        {#if $systemStatus.isRecording}
            <span class="recording">● Запись</span>
        {:else}
            <span class="idle">○ Ожидание</span>
        {/if}
    </div>

    <div class="status-item">
        <strong>Частота:</strong> {$systemStatus.frequency} Гц
    </div>

    <div class="status-item">
        <strong>Точек маршрута:</strong> {$realTimePath.length}
    </div>
</div>

<style>
  .status-bar {
    display: flex;
    gap: 24px;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    padding: 16px 24px;
    font-size: 14px;
    font-weight: 500;
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow:
        0 4px 20px rgba(0, 0, 0, 0.08),
        0 0 0 1px rgba(255, 255, 255, 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .status-bar:hover {
    box-shadow:
        0 8px 30px rgba(0, 0, 0, 0.12),
        0 0 0 1px rgba(255, 255, 255, 0.15);
    transform: translateY(-1px);
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: rgba(248, 250, 252, 0.6);
    border-radius: 12px;
    transition: all 0.2s ease;
    border: 1px solid rgba(226, 232, 240, 0.5);
  }

  .status-item:hover {
    background: rgba(241, 245, 249, 0.8);
    transform: scale(1.02);
  }

  .status-item strong {
    color: #475569;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .recording {
    color: #dc2626;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .recording::before {
    content: "";
    width: 8px;
    height: 8px;
    background: #dc2626;
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7);
  }

  .idle {
    color: #64748b;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .idle::before {
    content: "";
    width: 8px;
    height: 8px;
    background: #64748b;
    border-radius: 50%;
  }

  @keyframes pulse {
    0% {
        box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7);
    }
    70% {
        box-shadow: 0 0 0 6px rgba(220, 38, 38, 0);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(220, 38, 38, 0);
    }
  }

  @media (max-width: 1024px) {
    .status-bar {
        flex-wrap: wrap;
        gap: 16px;
        padding: 12px 20px;
    }

    .status-item {
        flex: 1;
        min-width: 140px;
        justify-content: center;
    }
  }

  @media (max-width: 768px) {
    .status-bar {
        border-radius: 12px;
        padding: 12px 16px;
        gap: 12px;
    }

    .status-item {
        min-width: 120px;
        padding: 6px 10px;
    }

    .status-item strong {
        font-size: 12px;
    }
  }
</style>
