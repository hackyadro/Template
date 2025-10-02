import type { Beacon, Position, SessionConfig } from '@/types';

export class RESTClient {
  private baseURL: string;
  
  constructor(baseURL: string = 'http://localhost:8000/api') {
    this.baseURL = baseURL;
  }
  
  async startSession(config: SessionConfig): Promise<string> {
    const response = await fetch(`${this.baseURL}/session/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.sessionId;
  }
  
  async stopSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/session/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to stop session: ${response.statusText}`);
    }
  }
  
  async savePath(sessionId: string, fileName: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/path/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId, fileName })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to save path: ${response.statusText}`);
    }
  }
  
  async getBeacons(): Promise<Beacon[]> {
    const response = await fetch(`${this.baseURL}/beacons`);
    
    if (!response.ok) {
      throw new Error(`Failed to get beacons: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.beacons;
  }
  
  async getPath(sessionId: string): Promise<Position[]> {
    const response = await fetch(`${this.baseURL}/session/${sessionId}/path`);
    
    if (!response.ok) {
      throw new Error(`Failed to get path: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.points;
  }
  
  async getSessionInfo(sessionId: string) {
    const response = await fetch(`${this.baseURL}/session/${sessionId}/info`);
    
    if (!response.ok) {
      throw new Error(`Failed to get session info: ${response.statusText}`);
    }
    
    return await response.json();
  }
}
