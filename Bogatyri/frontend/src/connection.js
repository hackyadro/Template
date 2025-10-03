import { beacons, systemStatus, realTimePath, currentPosition } from './stores.js';

class WebSocketService {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.flag = false;
    }

    connect(url) {
        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                systemStatus.update(status => ({ ...status, isConnected: true }));
                this.reconnectAttempts = 0;
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                systemStatus.update(status => ({ ...status, isConnected: false }));
                if (!this.flag) {
                    this.handleReconnect(url);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

        } catch (error) {
            console.error('WebSocket connection failed:', error);
        }
    }

    handleMessage(data) {
        if (data) {
            this.updatePath(data);
        }
    }

    updatePath(data) {
        realTimePath.update(currentPath => {
            return [...currentPath, {
                                        x: data.x,
                                        y: data.y
                                    }];
        });
        currentPosition.set({
            x: data.x,
            y: data.y
        });
    }

    handleReconnect(url) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

            setTimeout(() => {
                this.connect(url);
            }, 3000 * this.reconnectAttempts);
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

export const websocketService = new WebSocketService();
