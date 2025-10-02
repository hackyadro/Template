
import type { Beacon, Position, SessionConfig } from '@/types';
import type { StartSessionResponse, StopSessionResponse } from '@/types';

export class RESTClient {
  baseURL = 'http://localhost:8000/api';


  async startSession(cfg: SessionConfig): Promise<StartSessionResponse> {
    const res = await fetch(`${this.baseURL}/session/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cfg),
    });
    if (!res.ok) throw new Error(`Start failed: ${res.status} ${res.statusText}`);
    return res.json(); // { sessionId, status, ... }
  }

  async stopSession(sessionId: string): Promise<StopSessionResponse> {
    const res = await fetch(`${this.baseURL}/session/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId }),
    });
    if (!res.ok) throw new Error(`Stop failed: ${res.status} ${res.statusText}`);
    return res.json(); // { status, sessionId, ... }
  }

  async savePath(sessionId: string, fileName: string) {
    const res = await fetch(`${this.baseURL}/path/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId, fileName }),
    });
    if (!res.ok) throw new Error(`Save failed: ${res.status} ${res.statusText}`);
    return res.json();
  }

  async getBeacons() {
    const res = await fetch(`${this.baseURL}/beacons`);
    if (!res.ok) throw new Error(`Beacons failed: ${res.status} ${res.statusText}`);
    const data = await res.json();
    return data.beacons ?? [];
  }
}
