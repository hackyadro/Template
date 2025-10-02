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
  type: 'position_update' | 'session_status' | 'error';
  sessionId: string;
  position?: Position;
  status?: string;
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
