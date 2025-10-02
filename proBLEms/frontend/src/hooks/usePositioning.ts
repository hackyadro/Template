import { useState, useEffect, useCallback, useRef } from 'react';
import { RESTClient } from '@/api/rest-client';
import { WebSocketClient } from '@/api/websocket-client';
import type {
  Beacon,
  Position,
  SessionConfig,
  WebSocketMessage,
  StartSessionResponse,
  StopSessionResponse,
} from '@/types';
import { toast } from 'sonner';

export const usePositioning = () => {
  const [beacons, setBeacons] = useState<Beacon[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [currentPosition, setCurrentPosition] = useState<Position | undefined>();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<string>('No session');
  const [isLoading, setIsLoading] = useState(false);

  const restClientRef = useRef(new RESTClient());
  const wsClientRef = useRef(new WebSocketClient());

  useEffect(() => {
    loadBeacons();
    return () => wsClientRef.current.disconnect(); // гарантированно закрываем WS на размонтирование
  }, []);

  const loadBeacons = async () => {
    try {
      setIsLoading(true);
      const beaconsData = await restClientRef.current.getBeacons();
      setBeacons(beaconsData);
      toast.success(`Loaded ${beaconsData.length} beacons`);
    } catch (error) {
      console.error('Failed to load beacons:', error);
      toast.error('Failed to load beacons');
    } finally {
      setIsLoading(false);
    }
  };

  const handleWebSocketMessage = useCallback((data: WebSocketMessage) => {
    switch (data.type) {
      case 'position':
      case 'position_update': {
        if (data.position) {
          setPositions(prev => [...prev, data.position]);
          setCurrentPosition(data.position);
        }
        break;
      }
      case 'session_status': {
        const s = (data.status || '').toLowerCase();
        if (['started', 'subscribed', 'running', 'active'].includes(s)) {
          setSessionStatus('started'); // нормализуем как активное
        } else if (['stopped', 'finished', 'done'].includes(s)) {
          setSessionStatus('stopped');
          toast.info('Session stopped');
        } else if (s) {
          setSessionStatus(s);
        }
        break;
      }
      case 'error': {
        console.error('WebSocket error:', data.message);
        toast.error(data.message || 'An error occurred');
        setSessionStatus('error');
        break;
      }
    }
  }, []);

  const startSession = async (frequency: number, beaconMapId: string) => {
    try {
      setIsLoading(true);
      const config: SessionConfig = { frequency, beaconMapId };

      const resp: StartSessionResponse = await restClientRef.current.startSession(config);
      const newSessionId = resp.sessionId;
      if (!newSessionId) throw new Error('Backend did not return sessionId');

      // очищаем старые данные и активируем UI
      setSessionId(newSessionId);
      setPositions([]);
      setCurrentPosition(undefined);
      setSessionStatus('started');

      // подключаем WS и подписываемся
      await wsClientRef.current.connect();
      wsClientRef.current.onMessage(handleWebSocketMessage);
      wsClientRef.current.subscribe(newSessionId);

      toast.success(resp.message || 'Session started successfully');
    } catch (error) {
      console.error('Failed to start session:', error);
      toast.error('Failed to start session');
      setSessionStatus('error');
      wsClientRef.current.disconnect();
      setSessionId(null);
    } finally {
      setIsLoading(false);
    }
  };

  const stopSession = async () => {
    if (!sessionId) return;

    try {
      setIsLoading(true);
      const resp: StopSessionResponse = await restClientRef.current.stopSession(sessionId);

      // отключаемся от WS без автопереподключения
      wsClientRef.current.unsubscribe?.(sessionId);
      wsClientRef.current.disconnect();

      setSessionStatus(resp.status || 'stopped');
      setSessionId(null);
      setCurrentPosition(undefined);
      setPositions([]);

      const dur = typeof resp.duration_seconds === 'number' ? ` (${resp.duration_seconds.toFixed(1)}s)` : '';
      toast.success(`Session stopped${dur}`);
    } catch (error) {
      console.error('Failed to stop session:', error);
      toast.error('Failed to stop session');
    } finally {
      setIsLoading(false);
    }
  };

  // 🔑 активность: нужна и метка статуса, и наличие sessionId
  const isSessionActive = !!sessionId && !['No session', 'stopped', 'error'].includes(sessionStatus);

  const savePath = async (fileName: string) => {
    if (!sessionId) {
      toast.error('No active session');
      return;
    }
    try {
      setIsLoading(true);
      await restClientRef.current.savePath(sessionId, fileName);
      toast.success(`Path saved as: ${fileName}`);
    } catch (error) {
      console.error('Failed to save path:', error);
      toast.error('Failed to save path');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    beacons,
    positions,
    currentPosition,
    sessionStatus,
    isSessionActive,
    isLoading,
    startSession,
    stopSession,
    savePath,
    loadBeacons,
  };
};