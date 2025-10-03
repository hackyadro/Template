import type { WebSocketMessage } from '@/types';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private messageHandlers: ((data: WebSocketMessage) => void)[] = [];

  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;

  private shouldReconnect = true;       // <- флаг, чтобы НЕ реконнектиться после явного disconnect()
  private lastUrl: string | null = null;
  private lastSessionId: string | null = null; // <- чтобы автоподписаться после reconnect
  private sendQueue: any[] = [];        // <- очередь сообщений, если сокет ещё не открыт

  connect(url: string = 'ws://localhost:8000/api/ws'): Promise<void> {
    this.lastUrl = url;
    this.shouldReconnect = true; // явное подключение включает авто-reconnect

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;

          // отправляем всё, что накопили, включая подписку
          this.flushQueue();

          // если была активная подписка — восстановим её
          if (this.lastSessionId) {
            this.safeSend({ type: 'subscribe', sessionId: this.lastSessionId });
          }

          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data: WebSocketMessage = JSON.parse(event.data);
            this.messageHandlers.forEach(handler => handler(data));
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          // не вызываем reject повторно, если уже открылись; но тут в первый connect можно и отклонить
          // оставим как есть:
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          if (this.shouldReconnect && this.lastUrl) {
            this.attemptReconnect(this.lastUrl);
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private attemptReconnect(url: string): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this.connect(url).catch(error => {
          console.error('Reconnection failed:', error);
        });
      }, this.reconnectDelay);
    }
  }

  // Безопасная отправка: если сокет не открыт — очередь
  private safeSend(payload: any) {
    const raw = JSON.stringify(payload);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(raw);
    } else {
      this.sendQueue.push(raw);
    }
  }

  private flushQueue() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    while (this.sendQueue.length > 0) {
      const raw = this.sendQueue.shift();
      try { this.ws.send(raw); } catch (e) { console.error('WS send failed from queue', e); }
    }
  }

  subscribe(sessionId: string): void {
    this.lastSessionId = sessionId; // <- запоминаем, чтобы восстановить после reconnect
    this.safeSend({ type: 'subscribe', sessionId });
  }

  unsubscribe(sessionId: string): void {
    // сервер может не поддерживать 'unsubscribe'; это опционально
    this.safeSend({ type: 'unsubscribe', sessionId });
    // не сбрасываем lastSessionId здесь, чтобы при reconnect снова подписаться
    // если хотите очистить — раскомментируйте следующую строку:
    // this.lastSessionId = null;
  }

  onMessage(handler: (data: WebSocketMessage) => void): void {
    this.messageHandlers.push(handler);
  }

  disconnect(): void {
    // это "осознанное" отключение — реконнект НЕ нужен
    this.shouldReconnect = false;
    this.lastSessionId = null;     // при ручном стопе подписка больше не нужна
    this.sendQueue = [];           // и чистим очередь
    if (this.ws) {
      try { this.ws.close(); } catch {}
      this.ws = null;
    }
    this.messageHandlers = [];
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}