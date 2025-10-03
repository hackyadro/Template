export interface Beacon {
  id: string;
  x: number;
  y: number;
  uuid: string;
  major: number;
  minor: number;
  txPower: number;
}

export interface Position {
  x: number;
  y: number;
  timestamp: number;
  accuracy?: number;
}

export interface Session {
  id: string;
  status: 'started' | 'stopped' | 'error';
  startTime: number;
  points: Position[];
}

export interface WebSocketMessage {
  // сервер может прислать 'position' ИЛИ 'position_update'
  type: 'position' | 'position_update' | 'session_status' | 'error';
  sessionId: string;
  position?: Position;     // предпочтительно
  // для обратной совместимости, если сервер шлёт x,y напрямую — можно расширить при желании
  status?: string;         // 'started' | 'subscribed' | 'stopped' | ...
  message?: string;
  code?: string;
}

export interface SessionConfig {
  frequency: number;
  beaconMapId: string;
}

export interface SessionInfo {
  sessionId: string;
  status: string;
  startTime: number;
  pointsCount?: number;
  beaconsCount?: number;
}

export interface StartSessionResponse {
  sessionId: string;
  status: 'started' | 'error';
  beacons_loaded?: number;
  message?: string;
}

export interface StopSessionResponse {
  status: 'stopped' | 'error';
  sessionId: string;
  points_count?: number;
  duration_seconds?: number;
  message?: string;
}